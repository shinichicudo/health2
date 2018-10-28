#tensorflow配置,通用配置
max_step = 1001  # 最大迭代次数
learning_rate = 0.01   # 学习率
dropout = 0.5   # dropout时随机保留神经元的比例
batch_size = 500

layer_op_num = 32

# log_dir = 'E:\\data\\tensorflow\\logs\\ctptest12\\'    # 输出日志保存的路径

# train_dir = 'E:\\data\\marketdata\\train\\'
# test_dir = 'E:\\data\\marketdata\\test\\'



# linux下配置
# meta_path = '/usr/local/data/model/rb/rb15m/model.ckpt.meta'
# model_path = '/usr/local/data/model/rb/rb15m/model.ckpt'
# log_dir = '/usr/local/data/logs/'
#windows下配置
meta_path = 'E:/data/tensorflow/graghs/graph12/model.ckpt.meta'
model_path = 'E:/data/tensorflow/graghs/graph12/model.ckpt'
log_dir = 'logs/'





#ctp配置，测试账号1
# userid = '104214'
# password = 'important'
# brokerid = '9999'

#ctp配置，测试账号2
userid = '108483'
password = 'important123456'
brokerid = '9999'

#ctp配置,账号3
# userid = '71300813'
# password = '050013'
# brokerid = '0129'

test_reverse = False #False为从大到小，正常运行时排序;Ture为从小到大，测试时清仓用排序



ROW_LENGTH = 128
FIX_ROW_LENGTH = 64
MANUAL_SIZE = 10
LEAST_VOLUME_SIZE = 100000
NONE_SENSE_DATA_TYPE = 100
NOT_ORDER_DATA_TYPE = 0
CHECK_IMAGE_GROUP_SIZE = 10
ORDER_TO_NOT_ORDER = 100
RNN_MODEL_NAME ="rnn_model.h5"
LSTM_MODEL_NAME ="lstm_model.h5"
RNN_LSTM_MIX_MODEL_NAME ="rnn_lstm_mix_model.h5"

GENERAL_MODEL_NAME = str(FIX_ROW_LENGTH) + '_' + RNN_MODEL_NAME

PROFIT_AND_LOSS_RATIO = 2

DAY64_PREDICT = True

DAY128_PREDICT = True

GAIN_RATIO_64_p = 0.0225
LOSS_RATIO_64_p = 0.0193

GAIN_RATIO_64_n = 0.0169
LOSS_RATIO_64_n = 0.0139

GAIN_RATIO_128_p = 0.0392
LOSS_RATIO_128_p = 0.0249

GAIN_RATIO_128_n = 0.0226
LOSS_RATIO_128_n = 0.020

GAIN_PERCENT = 0.55
LOSS_PERCENT = 0.45
