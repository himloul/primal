library(osrm)
library(tidyverse)
library(lpSolve)
library(reshape2)

# Import Taxis
taxis = read.csv('taxis.csv', sep = ";")
taxis

# Import Users
users = read.csv('users.csv', sep = ";")
users

# Driving times matrix
dtm = osrmTable(src = taxis[,c("key","latitude", "longitude")], dst =  users[,c("key","latitude_p", "longitude_p")])$durations

#### FIRST MODEL : no capacity constraints ####

sol = lpSolve::lp.assign(cost.mat = dtm)$solution

opt = dtm
opt[] = sol

melt(opt) %>%
  filter(value != 0) %>%
  select(1:2)

reticulate::py_install("osrm", pip = T)

