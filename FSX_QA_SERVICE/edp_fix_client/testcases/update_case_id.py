import json

file_path = "/Users/zhenghuaimao/Desktop/qa-tools/edp_fix_client/initiator/edp_regression_test/testcases/EDP_Functional_Test_Matrix.json"

def update_case_id(case_file):
    with open(case_file, "r") as f:
        date = json.load(f)

    testCase = date["testCase"]
    for i, testCase in enumerate(testCase):
        if i == 0:
            testCase["Id"] = "1"
        else:
            testCase["Id"] = str(i + 1)

    with open(case_file, "w") as file:
        json.dump(date, file)
        print("id更新完成，请打开{}文件更新显示样式".format(file_path))



