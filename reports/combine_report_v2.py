'''
import os
import re

SECTIONS_DIR = "/home/ubuntu/graphgen_report/optimized_sections"
DIAGRAMS_DIR = "/home/ubuntu/graphgen_report/diagrams"
OUTPUT_FILE = "/home/ubuntu/graphgen_report/Optimized_GraphGen_Report.md"

def main():
    """Combines optimized sections and inserts diagrams to create the final report."""
    section_files = sorted([f for f in os.listdir(SECTIONS_DIR) if f.endswith(".txt")])
    
    full_report_content = []

    for section_file in section_files:
        section_path = os.path.join(SECTIONS_DIR, section_file)
        with open(section_path, "r", encoding="utf-8") as f:
            content = f.read()

        # In section 3, replace the ASCII diagram with the generated image.
        if "section_03" in section_file:
            # Use a regex to find the ASCII art block, as it's brittle to match exactly.
            ascii_art_pattern = re.compile(r"```\n┌.*?└─────────────────┘\n```", re.DOTALL)
            content = ascii_art_pattern.sub("![GraphGen 整体流程图](./diagrams/overall_flow.png)", content)

            # Insert other diagrams based on headers
            content = content.replace("#### 3.2.2 理解损失计算", 
                                      "#### 3.2.2 理解损失计算\n\n![ECE 理解评估流程图](./diagrams/ece_assessment.png)")
            content = content.replace("#### 3.2.3 子图采样策略", 
                                      "#### 3.2.3 子图采样策略\n\n![BFS 子图采样流程图](./diagrams/bfs_sampling.png)")

        # In section 4, insert the architecture and QA generation diagrams.
        if "section_04" in section_file:
            content = content.replace("#### 4.1.1 整体架构设计", 
                                      "#### 4.1.1 整体架构设计\n\n![系统架构图](./diagrams/system_architecture.png)")
            content = content.replace("### 4.5 QA生成实现", 
                                      "### 4.5 QA生成实现\n\n![QA 生成策略流程图](./diagrams/qa_generation.png)")

        full_report_content.append(content)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_report_content))

    print(f"Final report created at: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
'''
