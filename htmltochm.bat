@echo off
chcp 65001
set hhc_path="C:\Program Files (x86)\HTML Help Workshop\hhc.exe"
set source="C:\Users\DOC_GIT\DISTR_DOC\doc\"
set target="54_02.chm"

::                                          HTML       
echo [OPTIONS] > %source%\project.hhp
echo Compiled file=%target% >> %source%\project.hhp
echo [FILES] >> %source%\project.hhp
for /r %source% %%a in (*.htm,*.html) do (
  echo %%a >> %source%\project.hhp
)

::                       CHM     
%hhc_path% %source%\project.hhp

::          ,                  CHM
if not exist %target% (
  echo                       
  exit /b 1
)

echo                              
exit /b 0