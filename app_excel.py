import pandas as pd
import mylogger

class ExcelReaderWriter:
    def __init__(self):
        pass

    # 读取Excel文件
    def read_excel(self, excel_fullpath, sheet_name):
        try:
            df = pd.read_excel(excel_fullpath, sheet_name=sheet_name)
            return df
        except Exception as e:
            msg = f'Open Excel file {excel_fullpath} Exception: {e}'
            mylogger.error(msg)
            return None

    # 写入Excel文件
    def write_excel(self, df, excel_fullpath, sheet_name):
        try:
            with pd.ExcelWriter(excel_fullpath, engine='openpyxl', mode='w') as writer: 
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as e:
            msg = f'Save Excel file {excel_fullpath} Exception: {e}'
            mylogger.error(msg)

# if __name__ == '__main__':
#     excel_file_path = 'data.xlsx'
#     reader_writer = ExcelReaderWriter(excel_file_path)

#     # 写入sheet1的数据
#     df1 = pd.DataFrame({'name': ['Alice', 'Bob', 'Carol'], 'age': [20, 21, 22], 'gender': ['female', 'male', 'female']})
#     reader_writer.write_sheet('sheet1', df1)

#     # 写入sheet2的数据
#     df2 = pd.DataFrame({'name': ['Alice', 'Bob', 'Carol'], 'city': ['Beijing', 'Shanghai', 'Guangzhou']})
#     reader_writer.write_sheet('sheet2', df2)

#     # 读取sheet1的数据
#     sheet1 = reader_writer.read_sheet('sheet1')
#     print(sheet1)

#     # 读取sheet2的数据
#     sheet2 = reader_writer.read_sheet('sheet2')
#     print(sheet2)
