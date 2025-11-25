'''
import os

SECTIONS_DIR = "/home/ubuntu/graphgen_report/optimized_sections"
DIAGRAMS_DIR = "/home/ubuntu/graphgen_report/diagrams"
OUTPUT_FILE = "/home/ubuntu/graphgen_report/Optimized_GraphGen_Report.md"

def insert_diagram(content, placeholder, diagram_name, title):
    "Inserts a diagram into the content by replacing a placeholder."
    diagram_path = os.path.join("./diagrams", diagram_name)
    markdown_link = f"\n![{title}]({diagram_path})\n"
    return content.replace(placeholder, markdown_link)

def main():
    "Combines optimized sections and diagrams into a final report."
    section_files = sorted([f for f in os.listdir(SECTIONS_DIR) if f.endswith(".txt")])
    
    full_report_content = []

    for section_file in section_files:
        section_path = os.path.join(SECTIONS_DIR, section_file)
        with open(section_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "section_03" in section_file:
            # Placeholder for the ASCII art diagram
            ascii_art_placeholder = """```
┌─────────────────┐
│  原始文档集合   │
└────────┬────────┘
         │
         ▼
┌───────────────────────────────────┐
│  步骤1: 知识构建 (Knowledge         │
│         Construction)                │
│  - 文档分割                          │
│  - 实体/关系提取                     │
│  - 知识聚合                          │
└────────┬─────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│  步骤2: 理解评估 (Comprehension     │
│         Assessment)                 │
│  - 语义变体生成                      │
│  - 置信度评估                        │
│  - 理解损失计算                      │
└────────┬─────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│  步骤3: 图组织 (Graph Organization)  │
│  - 子图提取 (k-hop)                  │
│  - 边选择策略                        │
│  - 约束检查                          │
└────────┬─────────────────────────┘
         │
         ▼
┌───────────────────────────────────┐
│  步骤4: QA生成 (QA Generation)      │
│  - 原子QA生成                        │
│  - 聚合QA生成                        │
│  - 多跳QA生成                        │
└────────┬─────────────────────────┘
         │
         ▼
┌─────────────────┐
│  合成QA数据集   │
└─────────────────┘
```"""
            content = content.replace(ascii_art_placeholder, "![GraphGen 整体流程图](./diagrams/overall_flow.png)")
            content = insert_diagram(content, "#### 3.2.2 理解损失计算", "ece_assessment.png", "ECE 理解评估流程图")
            content = insert_diagram(content, "#### 3.2.3 子图采样策略", "bfs_sampling.png", "BFS 子图采样流程图")

        if "section_04" in section_file:
            content = insert_diagram(content, "#### 4.1.1 整体架构设计", "system_architecture.png", "系统架构图")
            content = insert_diagram(content, "### 4.5 QA生成实现", "qa_generation.png", "QA 生成策略流程图")

        full_report_content.append(content)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_report_content))

    print(f"Final report created at: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
'''
