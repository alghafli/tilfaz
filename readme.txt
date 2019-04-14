:Date: 2019-04-14
:Authors:
    * Mohammad Alghafli <thebsom@gmail.com>

Tilfaz, your home TV channel.

If you have kids, you probably have noticed that they LOVE to watch videos endlessly. I wanted to control that in my kids and also let them understand the concept of time and so I decided to write this application.

This application lets you set up a weekly or monthly schedule for your videos. For example, you have a cartoon series with 10 episodes and you let 1 episode to be played every Saturday at 9:30 a.m.

You can connect your computer to a large monitor and let the videos play on that monitor. In this case, you can control the programs schedule in the small screen and let the videos play on the large screen.

------------
Requirements
------------

- Tested on linux. Windows is taken into consideration but not tested
completely.
- Python 3.
- Install the following libraries for python 3. Most of them can be installed using pip command for python 3 (pip3 in my linux mint):
    - sqlalchemy
    - codi
    - appdirs
    - python-vlc
    - python-dateutil
    - pygobject   (in debain gnu linux you can use the command `sudo apt-get install python3-gi`)
    - libvlc. The easiest way to install libvlc is to install vlc media player
    itself.

------
Status
------

I have been using this application in a laptop for a few months and it runs
fine. For some reason, if the laptop screen is closed, the HDMI screen pauses
every 1 minute for around a second. If the laptop screen is open, no problem
everything is smooth.

--------
Tutorial
--------

Below is a brief description of how to use this application. I should make a
better tutorial someday.

-----------------------
Step 1: Run the program
-----------------------

It is preferable to attach an external larger monitor to your computer before running this application.

You should run the file `main.py` using python 3. In Debian like linux distributions, you can use the following command::

    python3 main.py

-----------------------------
Step 2: Knowing the interface
-----------------------------

The user interface of this application has 2 windows, the `video window` and the `main window`.

The `video window` is always on top and its size takes the full screen. There is nothing much you can do with it. Because this window is always on top, it will hide the `main window`. You can move the `video window` to another workspace or disable `always on top` option (press ALT+Space and you will see the option in the menu).

The `main window` is what you will be using most of the time. It has 3 pages:
1- `main page`. Here you will see all your programs. You can add a new program or edit your current programs.
2- `control page`. Not very useful. I will not explain it here and you do not need to use it at all. You can play with the buttons if you really want to know what you can do with it.
3- `options page`. Here you can change the program preferences.

---------
Main page
---------

Lets create a new TV program. Open the `main window` and go to the `main page`:
1- Press the "+" buttton at the top of the `main window` to create a new
program.
2- First field titled `name`. Write the name of your program. E.g. `Songs for Kids`.
3- Second field titled directory. Press the edit button to the right of the text field and choose a folder. This folder should contain all the video files you want to play as part of this program.
4- The `opening` and `ending` fields can be left empty. If you want, you can specify an opening video file and an ending video file. If specified, the opening file will be played before each episode of your program and the ending file will be played after each episode of your program.
5- You can see two text fields with the number "0" in them. This is the time of your program. We want it to start at 9:30 a.m. Write `9` in the left text field and `30` in the right text field. Use 24 hour format so if you want 9 p.m. you should write `21` for the hour.
6- To the right of the time you can see a button with the text `Weekly`. If you press it, your schedule will be monthly and you will specify which days of the month your program will play. We want our program to play every Saturday so we want a weekly schedule. Leave the button without change.
7- Below the time you will see a lot of check boxes for each day of the week (or the month if you chose monthly schedule). Choose the days you want your program to play at. For our example, enable Saturday and disable everything else.
8- Below the check boxes on the far left, you can see a combobox with three choices: normal, repeat and random. This decides the behaviour or your program. If you choose `normal`, every scheduled time for your program, a single episode will be played. The next scheduled time, the next episode will be played and so on. After the last episode, your program will stop playing. The video files are played in an alphabetical order. `repeat` is the same as `normal` but it will play the first episode after the last one so your program will never stop. `random` means a random episode will be played each time. If we have kids songs, we probably want them to `repeat` or be played in `random`. For a TV series, we probably want to use `normal`. Choose whatever you want.
9- The number just next to the combobox is the number of episodes played at each schedule time. In our kids songs example, say we want to play 5 songs every time. In this case we make this number 5. If the program mode is `random` and the number is 5, then 5 different files will be randomly played. No file will be played twice.
10- Next to the number of episodes is a combobox. This is the last file played. Leave it alone. It changes by itself everytime the program is played.
11- There are 2 things we did not see. There is a big button on the top left corner of the page. That is the thumbnail button. Click it and choose a picture that represents your program. The second thing is the `stopped` check box. If you enable it, your program will not play until it is disabled. Use it for temporarily stopping the program.
12- At the bottom you can see an empty list for Subprograms. Leave it alone for now. Another section below will be dedicated for it.
13- Finally, to add your program now, click the checkmark button at the bottom of the page.
14- Now you are back to the main page. Next to the "+" button we clicked to create a new program you can see an edit button to edit an existing program if you want.
15- In case you edit a program, clicking the `x` button at the bottom of the program page will cancel all your changes to the program. Clicking the trash button will delete your program. Pressing the back arrow button at the top of the page will go back to the `main page` without applying any changes to your program.

After all this, now your program is ready and will be played on schedule.

------------
Video window
------------

After creating a program, you can see a few things in the video window:
1- In the right you can see the image representing the next program that will play.
2- Top left you can see the time the next program will play. Below that you can see the program title.
3- At the bottom you can see the time (or number of days) left until your program is played. If there is less than or equeal to 1 minute left, the displayed number will be in seconds. The quick change in time can make kids very excited waiting for the program to start :)

------------
Options page
------------

The options window shows a lot of options for the program. Here I go through the most useful ones:

1- Language: The application language. Currently you can choose `ar` for Arabic. Anything else will make the program English. You can create your own translations if you want.
2- Video window font: the font family and size for the video window to show name of next program, time left and other text. There are other options for the video window. You can change them and see the effect.
3- Video monitor: You will see a list of all the screens attached to your computer. If you change this option, the video window will move to the screen specified in this option and will be resized to take up all the screen.

-----------
Subprograms
-----------

You may find this section useful but not always.

When you add (or edit) a program, you can see a `subprograms` table below with three buttons above it. It is used to create `subprograms` for your program. A subprogram is just another schedule for the same main program. For example, we made a program which runs every Saturday 9:30 a.m. Let's say we also want our program to also play every Saturday at 3:30 p.m. That is, it is played twice a day. To do that, create a subprogram useing the "+" button on the right. Write the time you want and choose the days you want similar to what you did in the main program. Choose the number of episodes you want in the subprogram schedule. There is one thing to note here. In the combobox, you can choose either `normal` or `repeat`. No `random`. The behaviour here is a little different. `normal` means use the same mode as the main program. So if the main is `random`, this will also be random at the time and days for the subprogram. `repeat` means play the same video files as the last time the program was played. So if your main program mode is `random` and the subprogram mode is `repeat`, the same randomly played files will play again in the new time. In order to confirm adding the new subprogram, click the checkmark at the bottom of the popover window.

The other two buttons above the subprogram table are the edit button and the "-" button. If you want to edit an existing subprogram, select it in the subprogram table and click teh edit button, make your changed and then confrim just like when you added a subprogram. If you want to delete a subprogram, select the subprogram in the subprograms table then click the "-" button.

------------
Config Files
------------

Tilfaz config files are stored in the configuration directory under the subdirectory "tilfaz" (in linux, that will be `~/.config/tilfaz/`)

However, if the programs sees a file named `tilfaz.cfg` in the same directory as the `main.py` file, it will run in portable mode and the config file and programs database will be in the same directory as `main.py`.

-----------
Final words
-----------

I hope this program is useful to you. Enjoy and let your kids enjoy too.

