
import os
from openai import OpenAI

# Initialize the client
client = OpenAI()

def optimize_text(text, section_name):
    """Optimizes the text of a report section using an LLM."""
    prompt = f"""
请在保持原有内容（尤其是代码和公式）不变的前提下，对以下技术报告的文字内容进行优化和完善，使其成为一份高质量的技术报告。请保持原有的Markdown格式。

**章节：** {section_name}

**原始内容：**
```markdown
{text}
```

**优化后的内容：**
"""

    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": "You are a professional technical writer. Your task is to refine and improve the language of a technical report to meet high academic and professional standards. Do not alter the core meaning, code snippets, or mathematical formulas. Preserve the original Markdown formatting."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
        max_tokens=4096,
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    sections_dir = "/home/ubuntu/graphgen_report/sections"
    optimized_dir = "/home/ubuntu/graphgen_report/optimized_sections"

    # Get the list of section files and sort them
    section_files = sorted([f for f in os.listdir(sections_dir) if f.endswith(".txt")])

    for section_file in section_files:
        section_path = os.path.join(sections_dir, section_file)
        optimized_path = os.path.join(optimized_dir, section_file)

        print(f"Optimizing {section_file}...")

        with open(section_path, "r", encoding="utf-8") as f:
            original_text = f.read()

        section_name = section_file.replace(".txt", "").replace("_", " ")
        optimized_content = optimize_text(original_text, section_name)

        with open(optimized_path, "w", encoding="utf-8") as f:
            f.write(optimized_content)

        print(f"Saved optimized section to {optimized_path}")

    print("\nAll sections optimized.")
