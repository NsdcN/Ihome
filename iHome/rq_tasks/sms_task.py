from rq_tasks.yuntongxun.ccp_sms import CCP


# 发送短信函数
def ccp_send_sms_code(mobile, sms_code):
    result = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    return result