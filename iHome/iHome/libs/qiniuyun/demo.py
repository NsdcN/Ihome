import time
from qiniu import Auth, put_file
from django.utils import timezone


class Qiniuyun(object):
    # 需要填写你的 Access Key 和 Secret Key
    def __init__(self):
        self.access_key = 'i620Uj8rifCCYHueGcAO8BtOWAkg_KHN3OoeEQ3V'
        self.secret_key = 'Ur2UE7tXhRRHlhSvoxcOHNMTWw_lFU1eCD_XORsp'

    def uploadimage(self, image_url):
        # 构建鉴权对象
        q = Auth(self.access_key, self.secret_key)
        # 要上传的空间
        bucket_name = 'ihome-38'
        # 上传到七牛后保存的文件名
        image_name = 'avatar' + timezone.localtime().strftime('%Y%m%d%H%M%S')
        key = image_name
        # 生成上传 Token，可以指定过期时间等
        token = q.upload_token(bucket_name, key, 3600 * 24 * 7)
        # 要上传文件的本地路径
        localfile = image_url
        info = put_file(token, key, localfile)
        print(info)
        return key

    def get_img_url(self, file_name):
        bucket_url = 'qetrkfm0g.bkt.clouddn.com'
        img_url = 'http://%s/%s' % (bucket_url, file_name)
        return img_url


if __name__ == '__main__':
    a = Qiniuyun()
    url = '/home/ubuntu/Desktop/home11.jpg'
    key = a.uploadimage(url)
    time.sleep(2)
    result = a.get_img_url(key)
    print(result)
