# read the parameters from index.cfg and loads them as enviroment variables
export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/:./

eval `cat configSHELL.cfg |  sed "s/\[//g" | sed "s/\]//g" | sed "s/u'/'/g" |sed "s/,/ /g" | sed "s/'//g" | sed "s/\$//g" | sed 's/\\\`//g'`


#cat index.cfg  | grep -v '^\[' | sed 's/ = /=/g' | sed 's/=\[/=/g' | sed 's/\]//g' | sed 's/=\(.*\)/="\1"/g' | sed 's/, / /g' | sed "s/'//g" | grep -v "direct_link" > params
#. params
