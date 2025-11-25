'''
import os

SECTIONS_DIR = "/home/ubuntu/graphgen_report/optimized_sections"
DIAGRAMS_DIR = "diagrams"  # Relative path for Markdown links
OUTPUT_FILE = "/home/ubuntu/graphgen_report/Optimized_GraphGen_Report.md"

def main():
    """Combines optimized sections and inserts diagrams to create the final report."""
    section_files = sorted([f for f in os.listdir(SECTIONS_DIR) if f.endswith(".txt")])
    
    full_report_content = []

    for section_file in section_files:
        section_path = os.path.join(SECTIONS_DIR, section_file)
        with open(section_path, "r", encoding="utf-8") as f:
            content = f.read()
        full_report_content.append(content)

    # Join all content first
    final_content = "\n\n".join(full_report_content)

    # --- Insert Diagrams --- #

    # 1. Overall Flow Diagram in Section 3.3
    # The original ASCII art was in section 3.3. We will add the diagram there.
    placeholder_3_3 = "### 3.3 算法详细步骤"
    diagram_3_3 = f"\n![GraphGen 整体流程图](./{DIAGRAMS_DIR}/overall_flow.png)\n"
    final_content = final_content.replace(placeholder_3_3, placeholder_3_3 + diagram_3_3)

    # 2. ECE Assessment Diagram in Section 3.2.2
    placeholder_3_2_2 = "#### 3.2.2 理解损失计算"
    diagram_3_2_2 = f"\n![ECE 理解评估流程图](./{DIAGRAMS_DIR}/ece_assessment.png)\n"
    final_content = final_content.replace(placeholder_3_2_2, placeholder_3_2_2 + diagram_3_2_2)

    # 3. BFS Sampling Diagram in Section 3.2.3
    placeholder_3_2_3 = "#### 3.2.3 子图采样策略"
    diagram_3_2_3 = f"\n![BFS 子图采样流程图](./{DIAGRAMS_DIR}/bfs_sampling.png)\n"
    final_content = final_content.replace(placeholder_3_2_3, placeholder_3_2_3 + diagram_3_2_3)

    # 4. System Architecture Diagram in Section 4.1.1
    placeholder_4_1_1 = "#### 4.1.1 整体架构设计"
    diagram_4_1_1 = f"\n![系统架构图](./{DIAGRAMS_DIR}/system_architecture.png)\n"
    final_content = final_content.replace(placeholder_4_1_1, placeholder_4_1_1 + diagram_4_1_1)

    # 5. QA Generation Diagram in Section 4.5
    placeholder_4_5 = "### 4.5 QA生成实现"
    diagram_4_5 = f"\n![QA 生成策略流程图](./{DIAGRAMS_DIR}/qa_generation.png)\n"
    final_content = final_content.replace(placeholder_4_5, placeholder_4_5 + diagram_4_5)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Final report created at: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
'''
