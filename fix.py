import json

# Fix config.json
with open('c:\\krithoathon\\data\\config.json', 'r') as f:
    config = json.load(f)

# The user mistakenly put their actual password here. Let's extract it.
actual_password = config['email'].get('password_env', '')
if actual_password and actual_password != 'EMAIL_PASSWORD':
    config['email']['password_env'] = 'EMAIL_PASSWORD'
    with open('c:\\krithoathon\\data\\config.json', 'w') as f:
        json.dump(config, f, indent=2)

# Fix .env file
with open('c:\\krithoathon\\.env', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith('EMAIL_PASSWORD='):
        continue
    new_lines.append(line)

# Add the correct password
new_lines.append(f'\nEMAIL_PASSWORD="{actual_password}"\n')

with open('c:\\krithoathon\\.env', 'w') as f:
    f.writelines(new_lines)
print('Fixed!')
