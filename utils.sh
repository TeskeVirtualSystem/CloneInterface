#!/bin/bash

###################################
#      _______     ______         #  
#     |_   _\ \   / / ___|        #
#       | |  \ \ / /\___ \        #
#       | |   \ V /  ___) |       #
#       |_|    \_/  |____/        #
#                                 #
###################################
#         TVS DClone Tool         #
#      Version				1.0	  #
#	  By: Teske Virtual Systems   #
#	  This tool is release under  #
#     GPL license, for more       #
#   details see license.txt file  #
###################################
#    http://www.teske.net.br      #
###################################


SUDO="gksudo"
NO_ARGS=0
function getSudo() {
	echo "Sudoed"
}

function getDiskSize()	{
	SIZE=`sudo fdisk -l $1  2>>/dev/null |grep $1: | awk '{print $3}'`
	UNIT=`sudo fdisk -l $1  2>>/dev/null |grep $1: | awk '{print $4}' |cut -d, -f1`
	if [ -z $SIZE ]
	then
		echo "Disco inexistente"
	else
		echo $SIZE $UNIT
	fi
}
function getDiskPartitions() {
	sudo parted $1 print |grep ^" "
}
function getDiskModel()	{
	sudo parted $1 print | head -n1 | cut -d: -f2
}
function getDisks() {
	DISKS=""
	for i in a b c d e f g h i j k l m n o p q r s t u v w x y z
	do
		TOUT=`sudo fdisk -l /dev/sd$i  2>>/dev/null |grep /dev/sd$i: | awk '{print $3}'`
		#ls /dev/sd$i 1>> /dev/null 2>> /dev/null
		#if [ $?" -eq 0 ]
		if [ -z $TOUT ]
		then
			break
		else
			if [ $i = "a" ]
			then	
				DISKS="/dev/sd$i"
			else
				DISKS="$DISKS,/dev/sd$i"
			fi	
		#else
			#break
		fi
	done
	echo $DISKS
}

if [ $# -eq "$NO_ARGS" ] 
then
	echo "Uso: cloneutils argumento"
fi

while getopts ":sgdm" Option
do
	case $Option in
		s )
			DISK=`echo $@ | awk '{print $2}'`
			if [ -z $DISK ]	
			then
				echo "Nenhum disco selecionado"
			else
				getDiskSize $DISK
			fi
		;;
		g )
			getDisks
		;;
		d	)
			DISK=`echo $@ | awk '{print $2}'`
			if [ -z $DISK ]
			then
				echo "Nenhum disco selecionado"
			else	
				getDiskPartitions $DISK
			fi
		;;
		m	)
			DISK=`echo $@ | awk '{print $2}'`
			if [ -z $DISK ] 
			then
				echo "Nenhum disco selecionado"
			else
				getDiskModel $DISK
			fi
		;;
		* )	
			echo $Option
		;;
	esac
done
#getDiskSize /dev/sda
