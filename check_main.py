with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("--- Current proxy lines ---")
for i, line in enumerate(content.split('\n')):
    if 'proxy' in line.lower() or 'router' in line.lower():
        print(f"{i}: {repr(line)}")
