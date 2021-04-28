#---------------------------
#   Import Libraries
#---------------------------
from collections import deque
import codecs
import json
import re
import os
import winsound
import ctypes

#---------------------------
#   [Required] Script Information
#---------------------------
ScriptName = "Superbife Sound Player"
Website = "https://twitch.tv/superbife_"
Description = "Play sounds from specific sound filenames from Twitch chat."
Creator = "Superbife"
Version = "1.0.0"

#---------------------------
#   Define Global Variables
#---------------------------
SoundDictionary = {}
settingsFile = os.path.join(os.path.dirname(__file__), "settings\settings.json")
SoundFilesDirectory = os.path.join(os.path.dirname(__file__), "sounds")
SoundPlaybackQueue = deque()
MessageBox = ctypes.windll.user32.MessageBoxW
MB_YES = 6

#---------------------------------------
#   Settings
#---------------------------------------
class SettingsClass:
    """"Loads settings from file if file is found if not uses default values"""
    #The 'default' variable names need to match UI_Config
    def __init__(self, settingsFile=None):
        if settingsFile and os.path.isfile(settingsFile):
            with codecs.open(settingsFile, encoding='utf-8-sig', mode='r') as f:
                self.__dict__ = json.load(f, encoding='utf-8-sig')

        else: #set variables if no settings file is found
            self.OnlyLive = True
            self.SoundListCommand = "!sounds"
            self.SoundListSeparator = " / "
            self.SoundListMsg = "Available sounds: {0}"
            self.Volume = 50
            self.UseCD = True
            self.StreamerIgnoreCD = True
            self.GlobalCooldown = 30
            self.GlobalCooldownMsg = "{0} the command is still on cooldown for {1} seconds!"
            self.UserCooldown = 30
            self.UserCooldownMsg = "{0} the command is still on user cooldown for {1} seconds!"

    def Reload(self, data, settingsFile):
        """Reload settings on save through UI"""
        self.__dict__ = json.loads(data, encoding='utf-8-sig')
        self.Save(settingsFile)

    def Save(self, settingsFile):
        """Save settings contained within the .json and .js settings files"""
        try:
            with codecs.open(settingsFile, encoding="utf-8-sig", mode="w+") as f:
                json.dump(self.__dict__, f, encoding="utf-8", ensure_ascii=False)
            with codecs.open(settingsFile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
                f.write("var settings = {0};".format(json.dumps(self.__dict__, indent=2, encoding='utf-8', ensure_ascii=False)))
        except ValueError:
            Parent.Log(ScriptName, "Failed to save settings to file.")

#---------------------------
#   Functions
#---------------------------
def Init():
    """Data on Load, required function"""
    #   Create Settings Directory
    directory = os.path.join(os.path.dirname(__file__), "settings")
    if not os.path.exists(directory):
        os.makedirs(directory)        
    global Settings
    Settings = SettingsClass(settingsFile)
    LoadSoundList()

def Tick():
    """Required tick function (Gets called during every iteration even when there is no incoming data)"""
    if SoundPlaybackQueue:
        if Parent.PlaySound(SoundPlaybackQueue[0], Settings.Volume*0.01):
            SoundPlaybackQueue.popleft()

def Execute(data):
    """Required Execute Data function. Main execution flow."""

    if Settings.OnlyLive and (Parent.IsLive() is False):
        return

    if not data.IsChatMessage():
        return

    if IsSoundListCommand(data):
        return

    soundName = GetSoundNameInMessage(data)
    if not soundName:
        return

    if IsOnCooldown(data, soundName):
        return

    PlaySound(data, soundName)

def IsSoundListCommand(data):
    """Return true or false depending on the message being the Sound List Command message or not"""
    if Settings.SoundListCommand != data.Message:
        return False

    soundListString = Settings.SoundListSeparator.join(SoundDictionary.keys())
    soundListMsg = Settings.SoundListMsg.format(soundListString)
    SendResp(data, soundListMsg)
    return True

def IsOnCooldown(data, soundName):
    """Return true if command is on cooldown and send cooldown message if enabled"""
    if not Settings.UseCD:
        return False

    if Parent.HasPermission(data.User, "Caster", "") and Settings.StreamerIgnoreCD:
        return False

    IsGlobalCooldown = Parent.IsOnCooldown(ScriptName, soundName)
    IsUserCooldown = Parent.IsOnUserCooldown(ScriptName, soundName, data.User)
    if not IsGlobalCooldown and not IsUserCooldown:
        return False

    globalCDD = Parent.GetCooldownDuration(ScriptName, soundName)
    userCDD = Parent.GetUserCooldownDuration(ScriptName, soundName, data.User)

    if globalCDD > userCDD:
        m_CooldownRemaining = globalCDD
        message = Settings.OnCooldown.format(data.UserName, m_CooldownRemaining)
    else:        
        m_CooldownRemaining = userCDD
        message = Settings.OnUserCooldown.format(data.UserName, m_CooldownRemaining)
    
    SendResp(data, message)
    return True

def GetSoundNameInMessage(data):
    """Get the first match of the Sound List entries in chat message"""
    soundName = None
    chatWords = data.Message.split()
    for chatWord in chatWords:
        if chatWord in SoundDictionary.keys():
            soundName = chatWord
            break
    return soundName

def PlaySound(data, soundName):
    """Execute the command if triggered"""
    EnqueueSoundFile(SoundDictionary[soundName])
    Parent.AddUserCooldown(ScriptName, soundName, data.User, Settings.UserCooldown)
    Parent.AddCooldown(ScriptName, soundName, Settings.GlobalCooldown)

def SendResp(data, message):
    """Sends message to Stream chat"""
    if data.IsChatMessage():
        Parent.SendStreamMessage(message)

def EnqueueSoundFile(soundFileName):
    """Adds an sound file from the sound folder to the play queue."""
    fullpath = os.path.join(SoundFilesDirectory, soundFileName)
    SoundPlaybackQueue.append(fullpath)

def LoadSoundList():
    """Loads the sounds from the folder into a global array"""
    global SoundDictionary
    SoundDictionary = {}
    for fileName in os.listdir(SoundFilesDirectory):
        if os.path.isfile(os.path.join(SoundFilesDirectory, fileName)):
            SoundDictionary[os.path.splitext(fileName)[0]] = fileName

def OpenSoundFolder():
    """Open specific sounds folder"""
    location = (os.path.dirname(os.path.realpath(__file__)))
    location += "/sounds/"
    os.startfile(location)

def SetDefaultSettings():
    """Set default settings function"""
    winsound.MessageBeep()
    returnValue = MessageBox(0, u"You are about to reset the settings, are you sure you want to continue?"
                             , u"Reset settings file?", 4)
    if returnValue == MB_YES:
        returnValue = MessageBox(0, u"Settings successfully restored to default values.\r\nPlease unselect then reselect the Script on the menu."
                                 , u"Reset complete!", 0)
        Settings = SettingsClass()
        Settings.Save(settingsFile)

def ReloadSettings(jsonData):
    """Reload settings on Save"""
    global Settings
    Settings.Reload(jsonData, settingsFile)
    LoadSoundList()

def Unload():
    """Called when a user reloads their scripts or closes the bot / cleanup stuff"""
    return

def ScriptToggled(state):
    """Notifies you when a user disables your script or enables it"""
    return