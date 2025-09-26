

# param is QLineEdit
def get_shot_name(input_take_name, input_take_no):
    take_no = 1
    str_take_no = input_take_no.text()
    if str_take_no is not None and len(str_take_no) > 0:
        take_no = int(str_take_no)
    take_no = '%03d' % take_no
    return input_take_name.text() + "_" + take_no
