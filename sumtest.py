#!/usr/bin/env python3

f = open("zhong_data_raw_1.bin","rb")
binfile = f.read()
f.close()

sum = 0 
for b in binfile[:-1]:
    sum = sum^b     #每个字节与校验码进行异或操作
    print("%d, %x , %s" %(sum,sum, bin(sum)))

print ((~sum & 0b11111111).to_bytes(1,"big")) #校验码按位取反
