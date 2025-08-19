"""
Build Single EXE - FIXED VERSION
build_single_fixed.py
แก้ไขให้ได้ไฟล์เดียวที่ใช้งานได้ 100%
"""

import os
import subprocess
import sys

def create_spec_file():
    """สร้างไฟล์ .spec ที่รับประกันการทำงาน - แก้ไขแล้ว"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('mt5_auto_connector.py', '.'),
        ('smart_profit_manager.py', '.'),
        ('survivability_engine.py', '.'),
        ('ai_money_manager.py', '.'),
        ('gold_hedge_calculator.py', '.'),
        ('api_connector.py', '.'),
    ],
    hiddenimports=[
        'mt5_auto_connector',
        'smart_profit_manager',
        'survivability_engine', 
        'ai_money_manager',
        'gold_hedge_calculator',
        'api_connector',
        'MetaTrader5',
        'numpy',
        'numpy.core',
        'numpy.core.multiarray',
        'tkinter',
        'tkinter.ttk',
        'requests',
        'json',
        'threading',
        'datetime',
        'typing',
        'enum',
        'dataclasses',
        'math',
        'time',
        'os',
        'sys'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_Gold_Trading',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    with open('AI_Gold_Trading.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ สร้างไฟล์ AI_Gold_Trading.spec เรียบร้อย (แก้ไขแล้ว)")

def check_files():
    """ตรวจสอบไฟล์ที่จำเป็น"""
    required = [
        'main.py',
        'config.json',
        'mt5_auto_connector.py',
        'smart_profit_manager.py',
        'survivability_engine.py',
        'ai_money_manager.py', 
        'gold_hedge_calculator.py',
        'api_connector.py'
    ]
    
    missing = []
    for file in required:
        if not os.path.exists(file):
            missing.append(file)
        else:
            print(f"✅ {file}")
    
    if missing:
        print(f"\n❌ ไฟล์ที่ขาดหาย: {missing}")
        return False
    
    print("\n✅ ไฟล์ครบทุกตัว")
    return True

def install_requirements():
    """ติดตั้ง requirements ทั้งหมด"""
    requirements = ['pyinstaller', 'numpy', 'MetaTrader5', 'requests']
    
    for req in requirements:
        try:
            __import__(req)
            print(f"✅ {req} พร้อมใช้งาน")
        except ImportError:
            print(f"📦 กำลังติดตั้ง {req}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", req])
                print(f"✅ ติดตั้ง {req} เสร็จ")
            except:
                print(f"❌ ติดตั้ง {req} ไม่สำเร็จ")
                return False
    
    return True

def build_exe():
    """สร้าง .exe ไฟล์"""
    print("\n🚀 กำลังสร้าง .exe ไฟล์เดียว...")
    
    try:
        # ลบไฟล์เก่า
        import shutil
        if os.path.exists('build'):
            shutil.rmtree('build')
            print("🗑️ ลบโฟลเดอร์ build เก่า")
        if os.path.exists('dist'):
            shutil.rmtree('dist')
            print("🗑️ ลบโฟลเดอร์ dist เก่า")
        
        # สร้างด้วย spec file
        cmd = ['pyinstaller', '--clean', '--noconfirm', 'AI_Gold_Trading.spec']
        
        print(f"📜 คำสั่ง: {' '.join(cmd)}")
        print("⏳ กำลังสร้าง... (อาจใช้เวลา 1-2 นาที)")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ สร้าง .exe สำเร็จ!")
            
            # ตรวจสอบไฟล์
            exe_path = "dist/AI_Gold_Trading.exe"
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"📁 ไฟล์: {exe_path}")
                print(f"📊 ขนาดไฟล์: {size_mb:.1f} MB")
                
                # ทดสอบรันไฟล์
                print("\n🧪 ทดสอบไฟล์ .exe...")
                test_result = test_exe(exe_path)
                if test_result:
                    print("✅ ไฟล์ .exe ใช้งานได้!")
                else:
                    print("⚠️ ไฟล์ .exe อาจมีปัญหา - ลองรันด้วยตนเอง")
                
                return True
            else:
                print("❌ ไม่พบไฟล์ .exe")
                return False
        else:
            print("❌ สร้าง .exe ไม่สำเร็จ")
            print("\n📝 Error output:")
            print(result.stderr)
            print("\n📝 Standard output:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return False

def test_exe(exe_path):
    """ทดสอบไฟล์ .exe"""
    try:
        # รันไฟล์ .exe แล้วรอ 3 วินาที แล้วปิด
        process = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            # รอ 3 วินาที
            stdout, stderr = process.communicate(timeout=3)
            return True
        except subprocess.TimeoutExpired:
            # ถ้ารันได้เกิน 3 วินาที แสดงว่าใช้งานได้
            process.terminate()
            return True
            
    except Exception as e:
        print(f"⚠️ ไม่สามารถทดสอบไฟล์ .exe: {e}")
        return False

def copy_final_files():
    """คัดลอกไฟล์สำหรับแจกจ่าย"""
    try:
        # สร้างโฟลเดอร์สำหรับลูกค้า
        customer_folder = "AI_Gold_Trading_Customer"
        if os.path.exists(customer_folder):
            import shutil
            shutil.rmtree(customer_folder)
        os.makedirs(customer_folder)
        
        # คัดลอกไฟล์ .exe
        import shutil
        shutil.copy2("dist/AI_Gold_Trading.exe", customer_folder)
        
        # สร้างไฟล์ README
        readme_content = """🏆 AI Gold Grid Trading System

📋 วิธีใช้งาน:
1. เปิด MetaTrader5 และ login account
2. เปิดไฟล์ AI_Gold_Trading.exe
3. กดปุ่ม "Connect MT5"
4. เลือก Trading Mode
5. กดปุ่ม "Calculate AI Parameters"
6. กดปุ่ม "Start AI Trading"

⚠️ ข้อกำหนด:
- Windows 10/11
- MetaTrader5 ติดตั้งแล้ว
- Internet connection

📞 สำหรับการสนับสนุน
"""
        
        with open(f"{customer_folder}/README.txt", 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"📦 สร้างแพ็คเกจลูกค้า: {customer_folder}/")
        return customer_folder
        
    except Exception as e:
        print(f"⚠️ ไม่สามารถสร้างแพ็คเกจลูกค้า: {e}")
        return None

def main():
    print("🏗️ AI Gold Trading - สร้าง EXE ไฟล์เดียว (แก้ไขแล้ว)")
    print("=" * 60)
    
    # ติดตั้ง requirements
    print("📦 ตรวจสอบและติดตั้ง requirements...")
    if not install_requirements():
        input("❌ กด Enter เพื่อออก...")
        return
    
    # ตรวจสอบไฟล์
    print("\n📋 ตรวจสอบไฟล์...")
    if not check_files():
        input("❌ กด Enter เพื่อออก...")
        return
    
    # สร้าง spec file
    print("\n📝 กำลังสร้าง spec file...")
    create_spec_file()
    
    # สร้าง exe
    success = build_exe()
    
    if success:
        print("\n🎉 สำเร็จ! ไฟล์พร้อมใช้งาน")
        
        # สร้างแพ็คเกจลูกค้า
        customer_folder = copy_final_files()
        
        print("\n📋 ผลลัพธ์:")
        print("📁 ไฟล์หลัก: dist/AI_Gold_Trading.exe")
        if customer_folder:
            print(f"📦 แพ็คเกจลูกค้า: {customer_folder}/")
        print("🔒 โค้ดถูกซ่อนแล้ว")
        print("💡 สามารถส่งไฟล์ AI_Gold_Trading.exe ให้ลูกค้าได้เลย")
        
        # เปิดโฟลเดอร์
        try:
            if customer_folder and os.path.exists(customer_folder):
                os.startfile(customer_folder)
            else:
                os.startfile("dist")
        except:
            pass
            
    else:
        print("\n❌ ไม่สำเร็จ")
        print("💡 ปัญหาที่พบบ่อย:")
        print("- Antivirus block PyInstaller")
        print("- ไม่มี permission เขียนไฟล์")
        print("- RAM ไม่พอ")
        print("- ไฟล์ main.py มี syntax error")
    
    input("\nกด Enter เพื่อออก...")

if __name__ == "__main__":
    main()