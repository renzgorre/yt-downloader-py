; YT Downloader NSIS Installer Script
; Requires NSIS 3.x and the MUI2 plugin

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ── App metadata ───────────────────────────────────────────────────────────────

!define APP_NAME        "YT Downloader"
!define APP_VERSION     "1.2.0"
!define APP_PUBLISHER   "Renz Aron Gorre"
!define APP_EXE         "YT Downloader.exe"
!define APP_UNINSTALLER "Uninstall YT Downloader.exe"
!define INSTALL_DIR     "$PROGRAMFILES64\YT Downloader"
!define REG_KEY         "Software\Microsoft\Windows\CurrentVersion\Uninstall\YTDownloader"
!define STARTMENU_DIR   "$SMPROGRAMS\YT Downloader"

; ── Installer settings ─────────────────────────────────────────────────────────

Name            "${APP_NAME} ${APP_VERSION}"
OutFile         "YT-Downloader-Setup.exe"
InstallDir      "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor    /SOLID lzma
SetCompressorDictSize 32

; ── MUI2 interface settings ────────────────────────────────────────────────────

!define MUI_ABORTWARNING
!define MUI_ICON           "assets\icon.ico"
!define MUI_UNICON         "assets\icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP   "assets\installer_banner.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "assets\installer_banner.bmp"

!define MUI_WELCOMEPAGE_TITLE    "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT     "This wizard will install ${APP_NAME} ${APP_VERSION} on your computer.$\r$\n$\r$\nYT Downloader lets you download YouTube videos and audio in any format — MP4, MKV, MP3, FLAC, and more.$\r$\n$\r$\nClick Next to continue."

!define MUI_FINISHPAGE_TITLE     "Installation Complete"
!define MUI_FINISHPAGE_TEXT      "${APP_NAME} has been installed successfully.$\r$\n$\r$\nOn first launch, use the Install buttons inside the app to set up ffmpeg and aria2c."
!define MUI_FINISHPAGE_RUN       "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT  "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK      "GitHub Repository"
!define MUI_FINISHPAGE_LINK_LOCATION "https://github.com/renzgorre/yt-downloader-py"

; ── Pages (installer) ──────────────────────────────────────────────────────────

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE      "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ── Pages (uninstaller) ────────────────────────────────────────────────────────

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; ── Language ───────────────────────────────────────────────────────────────────

!insertmacro MUI_LANGUAGE "English"

; ── Version info embedded in the setup EXE ────────────────────────────────────

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName"      "${APP_NAME}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductVersion"   "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName"      "${APP_PUBLISHER}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription"  "${APP_NAME} Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion"      "${APP_VERSION}"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright"   "© 2024 ${APP_PUBLISHER}"

; ── Installer section ──────────────────────────────────────────────────────────

Section "Install" SecMain

    SetOutPath "$INSTDIR"

    ; Copy main executable
    File "dist\YT Downloader.exe"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\${APP_UNINSTALLER}"

    ; Start Menu shortcuts
    CreateDirectory "${STARTMENU_DIR}"
    CreateShortcut "${STARTMENU_DIR}\${APP_NAME}.lnk"         "$INSTDIR\${APP_EXE}"
    CreateShortcut "${STARTMENU_DIR}\${APP_UNINSTALLER}.lnk"  "$INSTDIR\${APP_UNINSTALLER}"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

    ; Add/Remove Programs registry entry
    WriteRegStr   HKLM "${REG_KEY}" "DisplayName"          "${APP_NAME}"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"       "${APP_VERSION}"
    WriteRegStr   HKLM "${REG_KEY}" "Publisher"            "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${REG_KEY}" "InstallLocation"      "$INSTDIR"
    WriteRegStr   HKLM "${REG_KEY}" "UninstallString"      '"$INSTDIR\${APP_UNINSTALLER}"'
    WriteRegStr   HKLM "${REG_KEY}" "QuietUninstallString" '"$INSTDIR\${APP_UNINSTALLER}" /S'
    WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"          "$INSTDIR\${APP_EXE}"
    WriteRegStr   HKLM "${REG_KEY}" "URLInfoAbout"         "https://github.com/renzgorre/yt-downloader-py"
    WriteRegDWORD HKLM "${REG_KEY}" "NoModify"             1
    WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"             1

    ; Estimate installed size (in KB) — PyInstaller exe is ~40–60 MB
    WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize"        55000

SectionEnd

; ── Uninstaller section ────────────────────────────────────────────────────────

Section "Uninstall"

    ; Remove main executable and uninstaller
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\${APP_UNINSTALLER}"

    ; Remove install directory (only if empty after deleting above)
    RMDir  "$INSTDIR"

    ; Remove Start Menu shortcuts
    Delete "${STARTMENU_DIR}\${APP_NAME}.lnk"
    Delete "${STARTMENU_DIR}\${APP_UNINSTALLER}.lnk"
    RMDir  "${STARTMENU_DIR}"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Remove Add/Remove Programs registry entry
    DeleteRegKey HKLM "${REG_KEY}"

    ; NOTE: User data at %USERPROFILE%\.ytdownloader is intentionally kept.
    ; It contains the user's config, ffmpeg, and aria2c binaries.
    ; Ask the user if they want to remove it.
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Do you also want to remove your personal data?$\r$\n$\r$\n$PROFILE\.ytdownloader$\r$\n$\r$\nThis folder contains your settings, ffmpeg, and aria2c binaries. Removing it is optional." \
        IDNO skip_userdata

        RMDir /r "$PROFILE\.ytdownloader"

    skip_userdata:

SectionEnd
