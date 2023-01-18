#!/usr/bin/env python3

import wave
import matplotlib.pyplot as plt
import numpy as np

FN='zhongwen'      #文件名

obj = wave.open(FN+'.wav','r')
print( "Number of channels",obj.getnchannels())
print ( "Sample width",obj.getsampwidth())
print ( "Frame rate.",obj.getframerate())
print ("Number of frames",obj.getnframes())
print ( "parameters:",obj.getparams())

sample_freq = obj.getframerate()    #获取采样率，需为44100Hz，但目前未加判断
frames = obj.getnframes()           #获取音频总帧数 （采样率*时长）
#frames= 591000
signal_wave = obj.readframes(frames)    #获取波形
obj.close()

#获取音频数据
audio_array = np.frombuffer(signal_wave, dtype=np.int16)

buffer_num = 15  #判断周期的buffer帧数
threshold = -20000 #周期底部阈值

minpos_list = [0]  #周期底部位置
period = []     #周期间隔

#跳过开始的空白音
pos = 0
while (abs(audio_array[pos])<500):
    pos = pos + 1
a = audio_array[pos:]
num=frames-pos
time = num/ sample_freq
print (a)

#判断周期
pos = 0
last_pos = 0 
cur_pos = 0
flip = 1 # 波形是否翻转 默认周期先谷后峰，后一半数据会翻转

#获得周期关键帧frame时点
while pos<len(a):
    buf= a[pos:pos+buffer_num] * flip
    if min(buf) < threshold:    #最小值小于阈值
        if len(buf)<buffer_num:
            num = len(buf)
        else:
            num = buffer_num
        for k in range(0, num):
            if (buf[k] == min(buf)) and (a[pos+k]*flip < a[pos+k-1]*flip):  #获得当前区间内的最小值位置，且该最小值为下降沿结尾
                cur_pos = pos+k
                
        if (cur_pos - last_pos) > 5000 and last_pos !=0:    #最小值与前一最小值的时间差，如间隔大于5000帧，这判断为中间有一段空白，后续音频判断标准峰谷倒转
            flip = flip * -1
            print("flipped!",pos,last_pos,cur_pos,)
            pos = pos - buffer_num
            last_pos = cur_pos - buffer_num
        else:
            if ((cur_pos - last_pos) < buffer_num )and (a[cur_pos]*flip < a[last_pos]*flip):    #最小值与前一最小值的时间差小于Buffer帧数，但当前最小值更小（下降趋势），更新最小值位置列表中最新的一个位置为当前位置
                minpos_list[-1]=cur_pos
                last_pos = cur_pos
            elif (cur_pos - last_pos) > buffer_num :    ##最小值与前一最小值的时间差大于Buffer帧数，最小值位置列表中新增当前位置
                minpos_list.append(cur_pos)
                last_pos = cur_pos
    pos = pos+buffer_num
#print (minpos_list)    

#计算每个周期的frame数 
for i in range(1,len(minpos_list)):
    period.append(minpos_list[i]-minpos_list[i-1])
#print (period)


data=[]

#识别数据位
for i in range(0,len(period)):
    if period[i]>53 and period[i]<60:   #57帧，起始音
        data.append('N')
    elif period[i]>18 and period[i]<25: #20帧，切换音；#22帧，0
        data.append(0)
    elif period[i]>40 and period[i]<47: #44帧，1
        data.append(1)
    else:
        data.append('X')    #无法判断
    
#print (data)


jump=1      #跳过几个切换音，默认应为 1
bit=0
rcv_data=[]
pos=0
cur_byte=0
last_N=0

f=open(FN+"_data_struct.bin","w")

#还原数据
parts=[]    #记录分段位置
data_pos = 0
for i in range(0,len(data)):
    if (data[i]==0 or data[i]==1):
        if i>last_N+jump :      #在最后一个'N'起始音后跳过切换音
            cur_byte= 2**bit * data[i] + cur_byte   # bit -> byte 转换，低位在前
            bit = bit + 1
            if bit > 7 :
                rcv_data.append(cur_byte)
                data_pos = data_pos + 1
                bit = 0
                cur_byte=0
                f.write('D')
        else:
            f.write('J')
            parts.append(data_pos) #记录本段开始位置
    else:    
        if data[i] == 'N':
            last_N = pos
        f.write(data[i])
    pos = pos + 1
f.close()
parts.append(data_pos)
#print (rcv_data)

# 写入数据文件
for pos in range(1,len(parts)):
    f=open(F"{FN}_data_raw_{pos}.bin","wb")
    for i in range(parts[pos-1],parts[pos]):
        print ("%x "%rcv_data[i], end="")
        f.write(rcv_data[i].to_bytes(1,"big"))
    f.close()
    #print (pos)    


#制图
#times = np.linspace(0, time, num)

#plt.figure(figsize=(15, 5))
#plt.plot(times, a)
#plt.ylabel('Signal Wave')
#plt.xlabel('Time (s)')
#plt.xlim(0, time)
#plt.title('WAVE FORMAT')
#plt.show()
