import os
files = os.listdir('dist')
for f in files:
    os.remove(f'dist/{f}')

# Build the new package
os.system('python -m build')