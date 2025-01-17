import os
import dash
import uuid
from dash import html
from flask import request
import feffery_antd_components as fac
import feffery_utils_components as fuc
from dash.dependencies import Input, Output,State
import feffery_markdown_components as fmc

from openai import OpenAI
from pathlib import Path
import json
import fitz  # PyMuPDF
from termcolor import colored
import os
import configparser

app = dash.Dash(__name__)
suppress_callback_exceptions=True

# 通过LLM处理PDF文本
def process_page(client, MODEL: str,page_text: str, page_num: int,OUTPUT_JSON_PATH) -> list[str]:

    print(colored(f"\n📖 处理第 {page_num + 1} 页...", "yellow"))

    response = client.chat.completions.create(
        model=MODEL,
            # 输入LLM的提示词
    messages=[
                {"role": "system", "content": """
                分析此页面，如同你在学习一本书。

                跳过包含以下内容的页面：
                - 目录
                - 章节列表
                - 索引页面
                - 空白页面
                - 版权信息
                - 出版详情
                - 参考文献或书目
                - 致谢
                
                提取知识如果页面包含以下内容：
                - 解释重要概念的前言内容
                - 实际教育内容
                - 关键定义和概念
                - 重要论点或理论
                - 示例和案例研究
                - 显著发现或结论
                - 方法论或框架
                - 批判性分析或解释
                
                对于有效内容：
                - 将 has_content 设置为 true
                - 提取详细的、可学习的知识点
                - 包括重要引用或关键陈述
                - 捕获示例及其上下文
                - 保留技术术语和定义
                
                对于要跳过的页面：
                - 将 has_content 设置为 false
                - 返回空知识列表
                
                返回内容:
                - 请用JSON格式返回
                - 知识点键命名为"knowledge"
                - 返回语言为中文,并在后面持续使用中文
                - 非常重要:请一定要用中文返回内容
                """},
                {"role": "user", "content": f"页面文本: {page_text}"}
            ],
        response_format={
            'type': 'json_object'
        }
    )

    result = response.choices[0].message.content
    result = json.loads(result)

    if result.get("has_content") is True:
        return knowledge(result,OUTPUT_JSON_PATH)
    elif result.get("has_content") is False:
        print(colored("⏭️  跳过页面（无相关内容）", "yellow"))
        return []  # 返回空列表


# 知识库
def knowledge(result,OUTPUT_JSON_PATH):
    # 文件路径
    file_path = OUTPUT_JSON_PATH

    # 新数据（knowledge 字段）
    new_data = result.get("knowledge", [])  # 确保 new_data 是列表

    # 如果文件存在且不为空，读取现有数据
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):  # 如果数据不是列表，转换为列表
                    print(colored("⚠️ 文件内容不是列表，初始化新列表", "red"))
                    existing_data = []
            except json.JSONDecodeError:
                print(colored("⚠️ 文件内容不是有效的 JSON，初始化新列表", "red"))
                existing_data = []
    else:
        existing_data = []  # 如果文件不存在或为空，初始化一个空列表

    # 追加新数据到现有数据中
    existing_data.extend(new_data)

    # 将更新后的数据写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    print(colored("✅ 数据已追加并写入文件", "green"))
    return result

# 知识库总结成markdown
def knowledge_summary_to_markdown(client,MODEL,OUTPUT_JSON_PATH,OUTPUT_MD_PATH):
    # 读取 JSON 文件
    with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
        text = f.read()  # 将 JSON 文件内容解析为 Python 对象

    response = client.chat.completions.create(
        model=MODEL,
        # 输入LLM的提示词
        messages=[
            {"role": "system", "content": """创建所提供内容的综合摘要，格式简洁但详细，使用代码格式。
            
            使用代码格式：
            - ## 用于主标题
            - ### 用于子标题
            - 项目符号用于列表
            - `代码块` 用于任何代码或公式
            - **粗体** 用于强调
            - *斜体* 用于术语
            - > 块引用用于重要笔记
            
            仅返回代码摘要，不要在前后添加任何其他内容，如“以下是摘要”等"""},
            {"role": "user", "content": f"分析此内容：\n" + "\n".join(text)}
        ]
    )

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as file:
        file.write(response.choices[0].message.content)

    return(response.choices[0].message.content)


# 这里的app即为Dash实例
@app.server.route('/upload/', methods=['POST'])
def upload():
    '''
    构建文件上传服务
    :return:
    '''

    # 获取上传id参数，用于指向保存路径
    uploadId = request.values.get('uploadId')

    # 获取上传的文件名称
    filename = request.files['file'].filename

    # 基于上传id，若本地不存在则会自动创建目录
    try:
        os.mkdir(os.path.join('assets', uploadId))
    except FileExistsError:
        pass

    # 流式写出文件到指定目录
    with open(os.path.join('assets', uploadId, filename), 'wb') as f:
        # 流式写出大型文件，这里的10代表10MB
        for chunk in iter(lambda: request.files['file'].read(1024 * 1024 * 10), b''):
            f.write(chunk)

    return {'filename': filename}


# 前端页面布局
app.layout = html.Div(
    [
        html.Div(
            [
                fac.AntdRow(
                    [
                        fac.AntdUpload(
                            id='pdf-upload',
                            apiUrl='/upload/',
                            buttonContent='请上传pdf文件',
                            fileTypes=['pdf'],
                            fileListMaxLength=1
                        ),
                        # OpenAI API设置
                        fac.AntdButton(
                            'API设置', icon=fac.AntdIcon(icon='fc-settings'),
                            id='api-setting',
                            style={'margin-left': '10px'}
                        ),
                        html.Div(
                            [
                                fac.AntdButton(
                                    '一键AI速读',
                                    id='drawer-read-book-open',
                                    variant = 'solid',
                                    color = 'default',
                                    style={'margin-left': '15px'}
                                ),
                            ],
                            style={
                                'margin-left': 'auto'
                            }
                        ),
                    ],
                ),
            ]
        ),

        html.Div(
            id='pdf-render',
            style={
                'height': 'calc(100vh - 120px)',
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',
                'marginTop': '25px'
            }
        ),
        # 抽屉
        fac.AntdDrawer(
            [
                html.Div(
                    [
                        fac.AntdInput(addonBefore='阅读页数',placeholder='输入数字,为空表示全文',id='TEST_PAGES'),
                        fac.AntdButton('一键阅读',id='drawer-read-book-submit',style={'margin-top': '5px'})
                    ],
                    style={
                        'width': '100%',
                        'overflow': 'auto'
                    }
                ),
                html.Div(
                    fac.AntdSpin(
                        html.Div(id='drawer-read-book-content2'), 
                        text='正在阅读中,请等待几秒至几分钟',
                        style={
                            'margin-top': '20px',
                        }
                    ),
                    style={
                        'margin-top': '20px',
                        'height': '100%',
                        'width': '100%',
                        'overflow': 'auto'
                    }
                )
            ],
            title='一键AI速读', 
            width = '50%',
            id='drawer-read-book'
        ),
        # 对话框
        fac.AntdModal(
            '示例内容', 
            id='Modal_api_setting', 
            title='API设置',
            maskClosable=False,
            keyboard=False,
        ),
        html.Div(id='Message')
    ],
    style={
        'padding': '30px 25px 0 30px'# 上 右 下 左
    }
)



# pdf上传
@app.callback(
    Output('pdf-render', 'children'),
    Input('pdf-upload', 'lastUploadTaskRecord')
)
def render_pdf(lastUploadTaskRecord):

    if lastUploadTaskRecord:
        return html.Iframe(
            src='/assets/{}/{}'.format(lastUploadTaskRecord['taskId'], lastUploadTaskRecord['fileName']),
            style={
                'height': '100%',
                'width': '100%',
                'border': 'none'
            }
        )
    
    return fac.AntdEmpty(
        description='请先上传pdf文件'
    )

# API设置   
@app.callback(
    Output('Modal_api_setting', 'visible'),
    Output('Modal_api_setting', 'children'),
    Input('api-setting', 'nClicks'),
    prevent_initial_call=True,
    _allow_dynamic_callbacks=True
)
def api_setting(nCLicks):
    new_uuid = str(uuid.uuid4())

    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('APIKEY.ini')

    # 获取配置值
    url = config.get('API', 'API_URL', fallback='')
    key = config.get('API', 'APIKEY1', fallback='')
    model = config.get('API', 'MODEL', fallback='')

    # 动态创建回调
    @app.callback(
        Output(f'Message_{new_uuid}', 'children'),
        Input(f'API_setting_save_{new_uuid}', 'nClicks'),
        Input(f'API_setting_test_{new_uuid}', 'nClicks'),
        State(f'API_url_{new_uuid}', 'value'),
        State(f'API_APIKEY_{new_uuid}', 'value'),
        State(f'API_MODEL_{new_uuid}', 'value'),
    )
    def dynamic_demo_callback(save, test, url, key, model):
        # print(save, test, url, key, model)
        if save:
            config = configparser.ConfigParser()
            config['API'] = {
                'APIKEY1': key,
                'API_URL': url,
                'MODEL': model
            }

            try:
                with open('APIKEY.ini', 'w') as configfile:
                    config.write(configfile)
                return fuc.FefferyFancyMessage(
                    '保存成功',
                    type='success',
                    position='top-center'
                )
            except Exception as e:
                return fuc.FefferyFancyMessage(
                    f'保存失败: {str(e)}',
                    type='error',
                    position='top-center'
                )

        if test:
            config = configparser.ConfigParser()
            config.read('APIKEY.ini')

            try:
                client = OpenAI(api_key=key, base_url=url)
                MODEL = model

                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": "你好"},
                        {"role": "user", "content": "你好"}
                    ]
                )
                return fuc.FefferyFancyMessage(
                    '测试成功',
                    type='success',
                    position='top-center'
                )
            except Exception as e:
                return fuc.FefferyFancyMessage(
                    f'测试失败: {str(e)}',
                    type='error',
                    position='top-center'
                )
        return dash.no_update
        # 动态创建回调结束

    return True, html.Div(
        [
            fac.AntdInput(addonBefore='url', value=url, placeholder='兼容OPENAI的url', id=f'API_url_{new_uuid}'),
            fac.AntdInput(addonBefore='APIKEY', value=key, placeholder='兼容OPENAI的APIKEY', id=f'API_APIKEY_{new_uuid}', style={'margin-top': '5px'}),
            fac.AntdInput(addonBefore='Model', value=model, placeholder='MODEL', id=f'API_MODEL_{new_uuid}', style={'margin-top': '5px'}),
            fac.AntdButton('测试', id=f'API_setting_test_{new_uuid}', style={'margin-top': '10px'}),
            fac.AntdButton('保存', id=f'API_setting_save_{new_uuid}', type='primary', style={'margin-left': '30px'}),
            html.Div(id=f'Message_{new_uuid}')
        ]
    )




# 抽屉打开
@app.callback(
    Output('drawer-read-book', 'visible'),
    Input('drawer-read-book-open', 'nClicks'),
    prevent_initial_call=True,
)
def drawer(nCLicks):
    return True


# 一键阅读
@app.callback(
    Output('drawer-read-book-content2', 'children'),
    Input('drawer-read-book-submit', 'nClicks'),
    State('TEST_PAGES', 'value'),
    State('pdf-upload', 'lastUploadTaskRecord'),
    prevent_initial_call=True,
)
def drawer(nCLicks,TEST_PAGES,lastUploadTaskRecord):

    config = configparser.ConfigParser()
    config.read('APIKEY.ini')

    client = OpenAI(api_key=config['API']['APIKEY1'], base_url=config['API']['API_URL'])
    MODEL = config['API']['MODEL']
    OUTPUT_JSON_PATH = "book_analysis/knowledge_bases/{}.json".format(lastUploadTaskRecord['fileName'])
    OUTPUT_MD_PATH = "book_analysis/summaries/{}.md".format(lastUploadTaskRecord['fileName'])

    # 打开PDF文档
    src='{}/{}/{}'.format(Path("assets"),lastUploadTaskRecord['taskId'], lastUploadTaskRecord['fileName']),

    pdf_document = fitz.open(src[0])

    # 确定需要处理的页面数量，如果TEST_PAGES已定义则使用其值，否则使用文档的总页数
    pages_to_process = int(TEST_PAGES) if TEST_PAGES is not None else pdf_document.page_count

    # 打印处理页数的信息
    print(colored(f"\n📚 正在处理 {pages_to_process} 页...", "cyan"))

    # 遍历文档中的每一页，但不超过需要处理的页面数量
    for page_num in range(min(pages_to_process, pdf_document.page_count)):
        # 获取当前页的页面对象
        page = pdf_document[page_num]
        # 从当前页提取文本内容
        page_text = page.get_text()

        knowledge_base = process_page(client, MODEL,page_text, page_num,OUTPUT_JSON_PATH)

        print(knowledge_base) # 输出每页汇总

    md = knowledge_summary_to_markdown(client, MODEL,OUTPUT_JSON_PATH,OUTPUT_MD_PATH)

    return fmc.FefferyMarkdown(
            markdownStr=md,
            showCopyButton=True,
        )



if __name__ == '__main__':
    app.run_server(debug=True)
