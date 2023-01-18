#!/usr/bin/env python3
from pypinyin import lazy_pinyin
import wave
import numpy as np

#音频信号段，44100Hz
SILENCE = np.array([0]*12348)   #空白分割音，0.28秒无声
START = np.array(([-30000]*28+[30000]*29)*8192) #起始音：770Hz 的 10.6 秒（8192 个周期，1300 微秒/周期
TAPE_IN = np.array([-30000]*9+[30000]*11) #切换音：1/2个周期 400微秒/周期，接着是1/2周期的 500微秒/周期。这个“短零”表示标题和数据之间的转换 （前一半200微秒，后一半250微秒）
ZERO = np.array([-30000]*11+[30000]*11) #0：500微秒/周期
ONE = np.array([-30000]*22+[30000]*22) #1：1000微秒/周期

# 输入法注音/拼音符号按键键值映射
KEYMAPPING = { "a": b'\x82', "b": b'\x42', "c": b'\xc2', "d": b'\x22', "e": b'\xa2', "f": b'\x62', "g": b'\xe2', "h": b'\x12', "i": b'\x92', "j": b'\x52', "k": b'\xd2', "l": b'\x32', "m": b'\xb2', "n": b'\x72', "o": b'\xf2', "p": b'\x0a', "q": b'\x8a', "r": b'\x4a', "s": b'\xca', "t": b'\x2a', "u": b'\xaa', "v": b'\x6a', "w": b'\xea', "x": b'\x1a', "y": b'\x9a', "z": b'\x5a'}



####################################################
#   汉字处理部分
#   读取点阵字库、生成区位码、拼音
#
####################################################

def get_quwei(hanzi):   # 获取GBK编码的汉字的区位码
    #code = bytes(hanzi,"GBK")
    code=hanzi
    print (code)
    code_list = list(code)
    for i in range(len(code_list)):
        code_list[i] = code_list[i] - 0xa0
        
    print ("区位码: %d%d" % (code_list[0],code_list[1]))
    return code_list

def get_pycode(hanzi):  # 获取GBK编码汉字的拼音
    py = lazy_pinyin(hanzi.decode("GBK"))
    print ("拼音: %s" % py[0])
    return py[0]

def get_hanzi(code_list):   # 读取字库文件，返回16×16文字点阵信息
    offset = 32* (94*(code_list[0] - 1) + code_list[1] - 1)
    print ("字库文件偏移: %d" % offset)
    f = open ('HZK16','rb')
    f.seek(offset)
    text = f.read(32)
    print (text)
    text_list = list(text)
    
    pos = 0
    for by in text_list:
        for  i in range(8):
            if by >> 7 & 1:
                print("██",end="")
            else:
                print("░░",end="")
            by = by << 1
        pos = pos + 1
        
        if pos == 2:
            print("")
            pos = 0
    print ("十六进制码：")
    for by in text_list:
        print ("%02x "% by, end="")
    print ("")
    return text

####################################################
#   数据处理部分
#   将区位码、拼音、字形点阵、校验码处理成存储数据
#   组装各部分数据生成音频源数据
####################################################

def quwei2bin(code):    # 区位码转成存储格式的字节码
    return int(bin(code)[2:].rjust(16,'0')[::-1],2).to_bytes(2,"big")   #区位码二进制高低位翻转互换后转成字节码

def py2bin(py):     # 拼音转成存储格式的字节码（取拼音前三位作为输入法）
    if len(py)>3:
        py=py[:3]
    pybin = b''
    for b in py:
        pybin = pybin + KEYMAPPING[b]
    pybin = pybin + b'\x04'
    while len(pybin)<4:
        pybin = pybin + b'\x00'    
    return pybin

def validate2bin(text): # 返回两字节检验码
    return text[-1].to_bytes(1,"big") + int(bin(text[-1])[2:].rjust(8,"0")[4:][::-1].ljust(8,"0"),2).to_bytes(1,"big") #校验码第一个字节为文字点阵最后一个字节，第二个字节为该字节高四位置零后二进制高低位翻转互换再转成字节码
        

def hanzi2bin(hanzi):   # 返回某一GBK编码汉字的数据
    quwei = get_quwei(hanzi)
    text = get_hanzi(quwei)
    py = get_pycode(hanzi)    
    
    #数据格式(40字节）： | 2 Bytes：区位码 | 4 Bytes：注音/拼音码 | 32 Bytes：字形点阵 | 2 Bytes：字形校验 |
    return quwei2bin(quwei[0]*100+quwei[1]) + py2bin(py) + text + validate2bin(text)    

def sum2bin(data):  #整个数据段的校验码
    sum = 0 
    for b in data:
        sum = sum^b     #每个字节与校验码进行异或操作
    #print("%d, %x , %s" %(sum,sum, bin(sum)))

    return (~sum & 0b11111111).to_bytes(1,"big")    #校验码按位取反
    
def build_data(filename):   #根据输入的文字列表文件生成字库整体数据
    data = b''
    count = 0
    f = open(filename,"rb")
    while (hanzi:=f.read(2)):
        if len(hanzi)==2:
            #print (hanzi)
            data = data + hanzi2bin(hanzi)
            count = count + 1
    f.close()
    data = data + b'\xff\xff'
    print ("已生成汉字 %d 个，数据长度 %d" % (count, len(data)))
    print ("开始补足空余数据……")
    
    f = open("datatemplate1.bin","rb")
    binfile = f.read()
    f.close()
    
    data = data + binfile[len(data):-1]
    data = data + sum2bin(data)
    
    print ("已生成汉字字库数据，数据长度 %d"%len(data))
    return data

####################################################
#   音频处理部分
#   数据转音频处理，音频数据格式处理，生成音频文件
#
####################################################

def data2bit(data, flip):
    count=0
    wav = np.array([])
    for b in data:       #字串中的每个字符
        if count % 100 == 0:
            print ("■",end="", flush=True)
        for bit in range(0,8):  #每一位
            if (b & 1):
                wav = np.append(wav, ONE * flip)
            else:
                wav = np.append(wav, ZERO * flip)
            b = b >> 1
        count = count +1
    print("")
    return wav    

def build_wave(data, output):
    f = wave.open(output+'.wav','wb')
    f.setnchannels(1)	#设置通道数
    f.setsampwidth(2)	#设置采样宽度
    f.setframerate(44100)	#设置采样
    f.setcomptype('NONE','not compressed')	#设置采样格式  无压缩

    #第一部分，字库数据
    print("生成第一部分数据：")
    wav = np.repeat(SILENCE, 10)  #空白音频
    wav = np.append(wav, START)     #起始音10.6秒
    wav = np.append(wav, TAPE_IN)   #切换音

    wav = np.append(wav, data2bit(data,1))

    #第二部分，固定数据
    print("生成第二部分数据：")
    wav = np.append(wav, SILENCE)  #空白音频
    wav = np.append(wav, START * -1)     #起始音10.6秒
    wav = np.append(wav, TAPE_IN * -1)   #切换音    
    
    template = open("datatemplate2.bin","rb")
    binfile = template.read()
    template.close()
    wav = np.append(wav, data2bit(binfile,-1))
    wav = np.append(wav, SILENCE)  #空白音频

    wave_data=wav.astype(np.int16).tobytes() #将类型转为字节

    f.writeframes(wave_data)
    f.close()

if __name__=='__main__':
    fn = input("字表文件名：")
    data = build_data(fn+".txt")
    print ("开始生成音频文件 %s.wav，请稍候……" % fn)
    build_wave(data, fn)
    print ("音频文件已生成！")
    
