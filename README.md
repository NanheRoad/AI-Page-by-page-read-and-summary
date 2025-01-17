# 📚 AI 阅读书籍：逐页PDF知识提取与总结器

 `app.py` 脚本对PDF书籍进行智能逐页分析，系统地提取知识点并在指定间隔生成逐步总结。它逐页处理内容，允许对详细内容进行理解，同时保持书籍的上下文连贯性。

### 功能

- 📲 图形化界面
- 📚 自动化PDF书籍分析和知识提取
- 🤖 基于AI的内容理解和总结
- 💾 持久化知识库存储
- 📝 Markdown格式的总结
- 🚫 智能内容过滤（跳过目录、索引页等）
- 📂 组织良好的输出目录结构

## 如何使用

1. **设置**

   ```bash
   # 克隆仓库
   git clone [仓库地址]
   cd [仓库名称]

   # 安装依赖
   pip install -r requirements.txt
   ```
2. **配置**

   - 在项目目录下找到APIKEY_example.ini文件，该文件主要储存LLM的配置信息，将文件重命名为APIKEY.ini
3. **运行**

   ```bash
   python app.py # 进入图形化界面
   ```

### 工作原理

1. **加载知识库**: 它加载现有知识库（如果存在）。
2. **处理页面**: 它处理PDF的每一页，提取知识点并更新知识库。
3. **生成总结**: 它根据逐页的总结，在处理完所有页面后生成最终总结。
4. **保存结果**: 它将知识库和总结保存到各自的文件中。

### 目录

* **book_analysis/knowledge_bases**: 知识库，逐页阅读生成
* **book_analysis/summaries:** 文档总结

### 致谢

* 灵感来源与方法借鉴：[AI-reads-books-page-by-page](https://github.com/echohive42/AI-reads-books-page-by-page)
* 文档处理：[PyMuPDF](https://github.com/pymupdf/PyMuPDF)
* 图形界面：[feffery-antd-components](https://github.com/CNFeffery/feffery-antd-components)
