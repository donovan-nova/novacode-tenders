with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # Start skipping at auto_seed function body
    if 'async def auto_seed():' in line:
        new_lines.append(line)
        new_lines.append('    logger.info("Auto-seed disabled - using GitHub Actions scraper.")\n')
        skip = True
        continue
    # Stop skipping when we hit the next function/decorator
    if skip and (line.startswith('@') or (line.startswith('async def') and 'auto_seed' not in line) or line.startswith('def ')):
        skip = False
    if not skip:
        new_lines.append(line)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Done")
# Verify
with open('backend/main.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f.readlines()[14:30], start=15):
        print(f"{i}: {line}", end='')
