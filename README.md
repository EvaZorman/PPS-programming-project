# PPS-programming-project
A scalable and customizable simulator of inter-AS routing using BGP protocol.

### git quick guide
<b>First time ever?</b>

1. Install git!
2. Clone the repository
```
git clone https://github.com/EvaZorman/PPS-programming-project
```
3. enter the working directory
```
cd PPS-programming-project
```

<b>Want to start to write some code?</b>
1. Make sure you have the most recent version of the code
```
git pull
```
2. Create your own branch
```
git checkout -b feature/new_branch_desctiptive_name
```
3. Write code like crazy

<b>Ready to share with the world?</b>
1. Commit your work
```
git commit -m -a "short comment describing what changed since the last commit"
```
* git commit is local, you may do that as often as you wish. Usualy when you're finished writing some part of the feature, and you're happy with it but the feature is not yet done.
* Try to commit often. Small commits are easier to review and manage.

2. Push to remote branch
```
git push origin feature/new_branch_desctiptive_name
```
this will create a new branch on the server with your *commited* work

3. When you're ready, open a pull request on github requesting to merge your branch into master.

<b>Ready to work on the next feature?</b>

Make sure you're back on the master branch, and that you pulled all changes before making another new one
````
git checkout master
git pull
````
