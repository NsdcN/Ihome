import time
import datetime


def calday(date1, date2):
    """
    计算 两个日期 间的天数
    :param data1:
    :param data2:
    :return:
    """
    # 将 字符型 的时间 转换成 时间结构 格式
    date1 = time.strptime(date1, '%Y-%m-%d')
    date2 = time.strptime(date2, '%Y-%m-%d')
    date1 = datetime.datetime(date1[0], date1[1], date1[2])
    date2 = datetime.datetime(date2[0], date2[1], date2[2])
    result = (date2 - date1).days
    return result


def judgedate(order_obj, date1, date2):
    """
    判断 order_obj 租房使用期 是否在 date1 到 date2 时间区内
    :param order_obj: 存在的某一个 租房订单
    :param date1: 当前 订单内 租房的 起始时间
    :param date2: 当前 订单内 租房的 截止时间
    :return: 若条件成立, 返回 True,否则返回 False
    """
    date1 = time.strptime(date1, '%Y-%m-%d')
    date2 = time.strptime(date2, '%Y-%m-%d')
    # －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－
    exist_order_begin_date = time.strptime(str(order_obj.begin_date), '%Y-%m-%d')
    exist_order_end_date = time.strptime(str(order_obj.end_date), '%Y-%m-%d')
    # －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－
    # 存在以下情况
    # 1. 已有订单的 结束时间 在 当前订单的合约期内
    # 2. 已有订单的 合约期 在 当前订单的合约期内
    # 3. 已有订单的 开始时间 在 当前订单的合约期内
    # 4. 当前订单的合约期 在 已有订单的合约期内
    if (exist_order_end_date >= date1 and exist_order_end_date <= date2) \
            or (exist_order_begin_date >= date1 and exist_order_end_date <= date2) \
            or (exist_order_begin_date >= date1 and exist_order_end_date >= date2) \
            or (exist_order_begin_date <= date1 and exist_order_end_date >= date2):
        return False
    return True


if __name__ == '__main__':
    days = calday('2021-08-20', '2020-08-20')
    print(days)
