import numpy as np
def goldarray(size):
    a = 1
    b = 0.618
    c = b*b
    array = []
    array.append(a)
    array.append(b)
    array.append(c)
    for i in range(size-3):

        a = b
        b = c
        c = b*b/a
        array.append(c)
    return array

def weightarray(size,rightposition):
    ga = goldarray(size)
    wa = []
    for i in range(rightposition):
        wa.append((1-ga[rightposition-i])*2)
    wa.append(ga[0])
    for j in range(size-rightposition-1):
        wa.append((1-ga[j+1])*2)
    return wa

def back(returns):
    max_draw_down = 0
    temp_max_value = 0
    for i in range(1, len(returns)):
        temp_max_value = max(temp_max_value, returns[i-1])
        max_draw_down = min(max_draw_down, returns[i]/temp_max_value-1)
    return max_draw_down




print(goldarray(20))
print(weightarray(20,4))



