KERNEL_HEADERS:=/lib/modules/$(shell uname -r)/build
PWD:=$(shell pwd)
obj-m := adv7180.o

all:
	make -C $(KERNEL_HEADERS) M=$(PWD) modules

clean:      
	make -C $(KERNEL_HEADERS) M=$(PWD) clean
