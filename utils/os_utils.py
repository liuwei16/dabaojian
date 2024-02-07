from qiniu import Auth, put_file, put_data

# 配置七牛云信息
bucket_url = "s89ho4r3a.hn-bkt.clouddn.com"
q = Auth(access_key="snZtt2joMbrIP8IXUywdta6jHq4c9bWG_JvZfjcB", secret_key="LA-4bGOEeftqJq9CDBbhaBbhgwhvLSzVOKuH-Rf5")
def upload_img_qiniu(key, bucket_name="actiontos", body_type='file', file_path='', file_data=''):
    # generate token
    token = q.upload_token(bucket_name, key, 3600)
    if body_type == 'file':
        put_file(token, key, file_path)
    elif body_type == 'bin':
        put_data(token, key, file_data)
    # 获得七牛云服务器上file_name的图片外链
    img_url = 'http://%s/%s' % (bucket_url, key)
    return img_url

if __name__ == '__main__':
    img_url = upload_img_qiniu(key='1.png', file_path='1.png')
    print(img_url)