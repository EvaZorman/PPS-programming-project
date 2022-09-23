# PSP-programming-project setup guide
Here you can find the setup steps needed to be taken to ensure that the 
project will run smoothly even on your machine!
This will be changed once containerisation is included, but until then, 
time to use your native OS. Using the requirement.txt file will enable 
us to ensure we have the same environment and libraries installed, and 
hopefully reduce any "but it works on my machine!" talks :)

### Development (one-time!) setup steps
1. Within your project folder, make sure you will be using a virtual 
environment, to not pollute your own setup, by running
```
python3 -m venv venv
```
4. Source your virtual environment by running
```
# on Linux or MacOS
source venv/bin/activate

# In cmd.exe
venv\Scripts\activate.bat

# In PowerShell
venv\Scripts\Activate.ps1
```
5. Install any necessary dependencies
```
python3 -m pip install -r requirements.txt
```
All necessary dependencies are now installed, and the program can run
smooth like butter :)

Any time you close and re-open your terminal, make sure your virtual env. 
is sourced and used!

In a Python IDE such as e.g. Pycharm, you can ensure your IDE uses your 
created virtual env. by setting it in the properties of the project. If 
you've already created a virtual env. by using an IDE, **ignore all the 
steps and keep coding :)**.