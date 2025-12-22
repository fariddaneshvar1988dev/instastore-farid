import os
import re

def fix_intcomma_in_files():
    """اصلاح فیلتر intcomma در همه فایل‌های HTML"""
    template_dir = "templates"
    
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # جایگزینی intcomma با flatformat:0
                # از: {{ price|intcomma }}
                # به: {{ price|floatformat:0 }}
                new_content = re.sub(r'\|intcomma\b', '|floatformat:0', content)
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"✅ اصلاح شد: {file_path}")
                else:
                    print(f"✓ بدون تغییر: {file_path}")

if __name__ == "__main__":
    fix_intcomma_in_files()
    print("\n🎉 همه فایل‌ها اصلاح شدند!")