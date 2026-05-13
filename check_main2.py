with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines[:20]):
    print(f"{i}: {repr(line)}")
