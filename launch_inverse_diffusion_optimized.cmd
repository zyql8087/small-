@echo off
cd /d F:\TPMS
F:\Anaconda\envs\DL\python.exe -u F:\TPMS\train_inverse_diffusion.py --batch_size 4096 --val_batch_size 8192 --val_every 5 --amp 1>>F:\TPMS\inverse_diffusion_train.log 2>>F:\TPMS\inverse_diffusion_train.err.log
