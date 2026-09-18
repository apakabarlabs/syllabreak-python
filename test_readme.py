import re
from pathlib import Path


def extract_python_code_blocks(markdown_text):
    pattern = r"```python\n(.*?)\n```"
    blocks = re.findall(pattern, markdown_text, re.DOTALL)
    return blocks


def test_readme_examples():
    readme_path = Path(__file__).parent / "README.md"
    readme_text = readme_path.read_text()

    code_blocks = extract_python_code_blocks(readme_text)

    assert len(code_blocks) > 0, "No Python code blocks found in README.md"

    from syllabreak import Syllabreak

    for i, code in enumerate(code_blocks):
        lines = [
            line
            for line in code.split("\n")
            if not line.strip().startswith("from ") and not line.strip().startswith("import ")
        ]

        namespace = {"Syllabreak": Syllabreak}

        for line in lines:
            if line.startswith(">>> "):
                cmd = line[4:]
                if cmd.strip():
                    try:
                        result = eval(cmd, namespace)
                        if result is not None:
                            namespace["_"] = result
                    except SyntaxError:
                        exec(cmd, namespace)
            elif line.startswith("'") and not line.startswith("..."):
                expected = eval(line)
                if "_" in namespace:
                    actual = namespace["_"]
                    assert actual == expected, f"Block {i}: Expected {expected!r}, got {actual!r}"
