from app.models.database import create_tables

if __name__ == "__main__":
    print("正在初始化資料庫...")
    create_tables()
    print("資料庫初始化完成！")