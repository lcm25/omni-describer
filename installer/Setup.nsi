Unicode true
; Instalador e cópia portátil. Este arquivo é UTF-8 com BOM.
; Sem o BOM, o makensis lê o script como ACP e troca os acentos.
; File and LicenseData resolvem caminhos relativos a partir desta pasta.
; Passe -DSRCDIR e -DOUTFILE absolutos, e /INPUTCHARSET UTF8.
SetCompressor /SOLID lzma
ManifestDPIAware true
RequestExecutionLevel user

!ifndef APPNAME
  !define APPNAME "Descritudo"
!endif
!ifndef APPDISPLAY
  !define APPDISPLAY "Descritudo"
!endif
!ifndef APPVERSION
  !define APPVERSION "2.1.0"
!endif
!ifndef APPEXE
  !define APPEXE "Descritudo.exe"
!endif
!ifndef OUTFILE
  !define OUTFILE "Descritudo-Setup.exe"
!endif
!ifndef SRCDIR
  !define SRCDIR "${__FILEDIR__}\arquivos"
!endif
; A repo-root path such as installer\arquivos is opened under installer\ and misses
; the files. If that happens, use the arquivos folder next to this script.
!if /FileExists "${SRCDIR}\Licenca-de-uso.txt"
!else if /FileExists "${__FILEDIR__}\arquivos\Licenca-de-uso.txt"
  !undef SRCDIR
  !define SRCDIR "${__FILEDIR__}\arquivos"
!else
  !error "Licenca-de-uso.txt not found. Pass an absolute -DSRCDIR. Looked in ${SRCDIR} and ${__FILEDIR__}\arquivos."
!endif
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
!define SHELLVERB "Descritudo"
!define SHELLLABEL "Descrever com Descritudo"
!define SENDTO "Descrever com Descritudo.lnk"

!macro RegisterAssoc EXT
  WriteRegStr HKCU "Software\Classes\SystemFileAssociations\${EXT}\shell\${SHELLVERB}" "" "${SHELLLABEL}"
  WriteRegStr HKCU "Software\Classes\SystemFileAssociations\${EXT}\shell\${SHELLVERB}" "MultiSelectModel" "Player"
  WriteRegStr HKCU "Software\Classes\SystemFileAssociations\${EXT}\shell\${SHELLVERB}\command" "" '"$INSTDIR\${APPEXE}" "%1"'
!macroend
!macro UnregisterAssoc EXT
  DeleteRegKey HKCU "Software\Classes\SystemFileAssociations\${EXT}\shell\${SHELLVERB}"
!macroend

Name "${APPDISPLAY} ${APPVERSION}"
OutFile "${OUTFILE}"
BrandingText "${APPDISPLAY} ${APPVERSION}"
InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${APPVERSION}.0"
VIAddVersionKey /LANG=1046 "ProductName" "${APPDISPLAY}"
VIAddVersionKey /LANG=1046 "FileDescription" "Instalador do ${APPDISPLAY}"
VIAddVersionKey /LANG=1046 "FileVersion" "${APPVERSION}"
VIAddVersionKey /LANG=1046 "ProductVersion" "${APPVERSION}"
VIAddVersionKey /LANG=1046 "LegalCopyright" "Omni Describer por Draqoken (audioses), licença MIT. Adaptação de Leandro Maruci."
VIAddVersionKey /LANG=1046 "CompanyName" "Leandro Maruci"

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"
!include "FileFunc.nsh"

Var Atualizar
Var Modo
Var RadInstalar
Var RadPortatil
Var ChkDesktop
Var ChkMenu
Var ChkGuia
Var OptDesktop
Var OptMenu
Var OptGuia
Var DirEscolhidaPeloUsuario
Var NaPaginaApoio
Var BtnPix

!define MUI_CUSTOMFUNCTION_ABORT AoCancelar
!define MUI_UNABORTWARNING

!define MUI_WELCOMEPAGE_TITLE "Bem-vindo ao assistente do ${APPDISPLAY} ${APPVERSION}"
!define MUI_WELCOMEPAGE_TEXT "Este assistente instala o ${APPDISPLAY} no computador ou cria uma cópia portátil em uma pasta ou pen drive.$\r$\n$\r$\nO ${APPDISPLAY} foi adaptado e melhorado por Leandro Maruci. Baseado no Omni Describer, criado por Draqoken (audioses), licença MIT.$\r$\n$\r$\nUse Tab para percorrer os controles, as setas para mudar a opção e Enter para avançar."
!insertmacro MUI_PAGE_WELCOME

!define MUI_LICENSEPAGE_TEXT_TOP "Leia a licença. Use as setas ou Page Down para percorrer o texto. A licença MIT original está no final."
!define MUI_LICENSEPAGE_TEXT_BOTTOM "Para continuar, é preciso aceitar a licença."
!define MUI_LICENSEPAGE_BUTTON "&Aceito"
!insertmacro MUI_PAGE_LICENSE "${SRCDIR}\Licenca-de-uso.txt"

Page custom PaginaModo PaginaModoSair
Page custom PaginaAtalhos PaginaAtalhosSair

!define MUI_PAGE_CUSTOMFUNCTION_PRE PastaPre
!define MUI_PAGE_CUSTOMFUNCTION_SHOW PastaShow
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE PastaSair
!insertmacro MUI_PAGE_DIRECTORY

!insertmacro MUI_PAGE_INSTFILES

Page custom PaginaApoio PaginaApoioSair

!define MUI_FINISHPAGE_TITLE "Concluído"
!define MUI_FINISHPAGE_TEXT "O ${APPDISPLAY} foi preparado em:$\r$\n$INSTDIR$\r$\n$\r$\nNa cópia portátil, as configurações ficam na pasta Dados, ao lado do programa."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPEXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Abrir o ${APPDISPLAY} agora"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\doc\pt_BR\help.html"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Abrir o guia de uso"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"

Function .onInit
  StrCpy $Modo "instalar"
  StrCpy $OptDesktop ${BST_CHECKED}
  StrCpy $OptMenu ${BST_CHECKED}
  StrCpy $OptGuia ${BST_CHECKED}
  StrCpy $DirEscolhidaPeloUsuario "0"
  StrCpy $Atualizar "0"
  StrCpy $NaPaginaApoio "0"

  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/ATUALIZAR" $1
  ${IfNot} ${Errors}
    StrCpy $Atualizar "1"
  ${EndIf}
  ClearErrors
  ${GetOptions} $0 "/PORTATIL" $1
  ${IfNot} ${Errors}
    StrCpy $Modo "portatil"
    ${If} $INSTDIR == "$LOCALAPPDATA\Programs\${APPNAME}"
      StrCpy $INSTDIR "$DOCUMENTS\${APPNAME} Portatil"
    ${EndIf}
  ${EndIf}

  ReadRegStr $0 HKCU "${UNINSTKEY}" "InstallLocation"
  ${If} $0 != ""
  ${AndIf} $Modo == "instalar"
    StrCpy $INSTDIR $0
  ${EndIf}
FunctionEnd

Function AoCancelar
  ${If} $NaPaginaApoio == "1"
    SendMessage $HWNDPARENT ${WM_COMMAND} 1 0
    Abort
  ${EndIf}
  MessageBox MB_YESNO|MB_ICONEXCLAMATION "Deseja realmente cancelar e sair do assistente do ${APPDISPLAY}?" IDYES +2
  Abort
FunctionEnd

Function PaginaApoio
  ; Sempre visível: instalação, atualização e cópia portátil.
  StrCpy $NaPaginaApoio "0"

  !insertmacro MUI_HEADER_TEXT "Apoie o projeto" "Opcional. Enter ou Esc continuam."
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}
  StrCpy $NaPaginaApoio "1"

  ${NSD_CreateLabel} 0 0 100% 78u "O ${APPDISPLAY} foi adaptado e melhorado por Leandro Maruci. Baseado no Omni Describer, criado por Draqoken (audioses), licença MIT. O programa é gratuito. Sua ajuda, de qualquer valor, mantém as atualizações. Copie a chave Pix pelo botão abaixo."
  Pop $0

  ${NSD_CreateButton} 0 86u 50% 16u "&Copiar chave Pix"
  Pop $BtnPix
  ${NSD_OnClick} $BtnPix CopiarPix

  GetDlgItem $0 $HWNDPARENT 1
  SendMessage $0 ${WM_SETTEXT} 0 "STR:&Continuar"
  GetDlgItem $0 $HWNDPARENT 2
  EnableWindow $0 1

  ${NSD_SetFocus} $BtnPix
  nsDialogs::Show
FunctionEnd

Function PaginaApoioSair
  StrCpy $NaPaginaApoio "0"
FunctionEnd

Function CopiarPix
  Pop $0
  StrCpy $2 "+5521977425383"
  System::Call 'user32::OpenClipboard(p $HWNDPARENT) i .r1'
  ${If} $1 = 0
    MessageBox MB_OK|MB_ICONEXCLAMATION "Não foi possível usar a área de transferência agora. Tente de novo."
    Return
  ${EndIf}
  System::Call 'user32::EmptyClipboard()'
  StrLen $3 $2
  IntOp $3 $3 + 1
  IntOp $3 $3 * 2
  System::Call 'kernel32::GlobalAlloc(i 0x0042, p r3) p .r4'
  System::Call 'kernel32::GlobalLock(p r4) p .r5'
  System::Call 'kernel32::lstrcpyW(p r5, w r2)'
  System::Call 'kernel32::GlobalUnlock(p r4)'
  System::Call 'user32::SetClipboardData(i 13, p r4)'
  System::Call 'user32::CloseClipboard()'
  MessageBox MB_OK|MB_ICONINFORMATION "Chave Pix copiada"
FunctionEnd

Function PaginaModo
  !insertmacro MUI_HEADER_TEXT "Tipo de uso" "Escolha como deseja usar o ${APPDISPLAY}."
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 24u "O que você deseja fazer? Use as setas para cima e para baixo para escolher."
  Pop $0

  ${NSD_CreateRadioButton} 0 28u 100% 40u "&Instalar no computador (recomendado). Instala só para o seu usuário, sem permissão de administrador, cria atalhos e aparece em Aplicativos instalados."
  Pop $RadInstalar
  ${NSD_AddStyle} $RadInstalar ${WS_GROUP}|${BS_MULTILINE}|${BS_TOP}

  ${NSD_CreateRadioButton} 0 76u 100% 40u "Criar cópia &portátil. Copia o programa para a pasta escolhida. Não cria atalhos nem altera o registro. As configurações ficam na pasta Dados, ao lado do programa. Para remover, apague a pasta."
  Pop $RadPortatil
  ${NSD_AddStyle} $RadPortatil ${BS_MULTILINE}|${BS_TOP}

  ${If} $Modo == "portatil"
    ${NSD_Check} $RadPortatil
    ${NSD_SetFocus} $RadPortatil
  ${Else}
    ${NSD_Check} $RadInstalar
    ${NSD_SetFocus} $RadInstalar
  ${EndIf}
  nsDialogs::Show
FunctionEnd

Function PaginaModoSair
  StrCpy $1 $Modo
  ${NSD_GetState} $RadPortatil $0
  ${If} $0 == ${BST_CHECKED}
    StrCpy $Modo "portatil"
  ${Else}
    StrCpy $Modo "instalar"
  ${EndIf}
  ${If} $1 != $Modo
  ${OrIf} $DirEscolhidaPeloUsuario == "0"
    ${If} $Modo == "portatil"
      StrCpy $INSTDIR "$DOCUMENTS\${APPNAME} Portatil"
    ${Else}
      ReadRegStr $0 HKCU "${UNINSTKEY}" "InstallLocation"
      ${If} $0 != ""
        StrCpy $INSTDIR $0
      ${Else}
        StrCpy $INSTDIR "$LOCALAPPDATA\Programs\${APPNAME}"
      ${EndIf}
    ${EndIf}
  ${EndIf}
FunctionEnd

Function PaginaAtalhos
  ${If} $Modo != "instalar"
    Abort
  ${EndIf}
  !insertmacro MUI_HEADER_TEXT "Atalhos" "Escolha quais atalhos criar."
  nsDialogs::Create 1018
  Pop $0
  ${NSD_CreateLabel} 0 0 100% 20u "Marque ou desmarque cada opção com a barra de espaço. Tab passa para a próxima."
  Pop $0
  ${NSD_CreateCheckBox} 0 26u 100% 12u "Criar atalho na área de &trabalho"
  Pop $ChkDesktop
  ${NSD_SetState} $ChkDesktop $OptDesktop
  ${NSD_CreateCheckBox} 0 44u 100% 12u "Criar atalho no &Menu Iniciar"
  Pop $ChkMenu
  ${NSD_SetState} $ChkMenu $OptMenu
  ${NSD_CreateCheckBox} 0 62u 100% 12u "Incluir no Menu Iniciar o &guia de uso"
  Pop $ChkGuia
  ${NSD_SetState} $ChkGuia $OptGuia
  ${NSD_SetFocus} $ChkDesktop
  nsDialogs::Show
FunctionEnd

Function PaginaAtalhosSair
  ${NSD_GetState} $ChkDesktop $OptDesktop
  ${NSD_GetState} $ChkMenu $OptMenu
  ${NSD_GetState} $ChkGuia $OptGuia
FunctionEnd

Function PastaPre
FunctionEnd

Function PastaShow
  ${If} $Modo == "portatil"
    !insertmacro MUI_HEADER_TEXT "Pasta da cópia portátil" "Escolha onde a cópia portátil será criada."
  ${Else}
    !insertmacro MUI_HEADER_TEXT "Pasta de instalação" "Escolha onde o ${APPDISPLAY} será instalado."
  ${EndIf}
  FindWindow $0 "#32770" "" $HWNDPARENT
  GetDlgItem $1 $0 1006
  ${If} $Modo == "portatil"
    SendMessage $1 ${WM_SETTEXT} 0 "STR:A cópia portátil será criada na pasta abaixo. As configurações ficam na pasta Dados, ao lado do programa. Para escolher outra pasta, digite o caminho ou use Procurar."
  ${Else}
    SendMessage $1 ${WM_SETTEXT} 0 "STR:O ${APPDISPLAY} será instalado na pasta abaixo. A pasta padrão fica no seu perfil do Windows e não pede permissão de administrador. Evite Arquivos de Programas."
  ${EndIf}
FunctionEnd

Function PastaSair
  StrCpy $DirEscolhidaPeloUsuario "1"
  StrLen $2 "$PROGRAMFILES"
  StrCpy $3 $INSTDIR $2
  StrLen $4 "$PROGRAMFILES64"
  StrCpy $5 $INSTDIR $4
  ${If} $3 == "$PROGRAMFILES"
  ${OrIf} $5 == "$PROGRAMFILES64"
    MessageBox MB_YESNO|MB_ICONEXCLAMATION "A pasta escolhida fica em Arquivos de Programas. A cópia portátil grava a pasta Dados ao lado do programa, e o Windows costuma impedir essa gravação ali.$\r$\n$\r$\nDeseja escolher outra pasta?" IDNO +2
    Abort
  ${EndIf}
FunctionEnd

Section "Principal" SecPrincipal
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /r "${SRCDIR}\*.*"

  ${If} $Modo == "portatil"
    FileOpen $0 "$INSTDIR\portable.txt" w
    FileWrite $0 "portable$\r$\n"
    FileClose $0
    ; A cópia portátil não leva as configurações nem as chaves de quem instalou.
    Delete "$INSTDIR\settings.dat"
    Delete "$INSTDIR\settings.dat2"
    Delete "$INSTDIR\settings.dat.json"
    Delete "$INSTDIR\key.salt"
    Delete "$INSTDIR\prompts.json"
    Delete "$INSTDIR\voices.json"
    RMDir /r "$INSTDIR\Dados"
    DetailPrint "Cópia portátil criada. As configurações ficarão na pasta Dados, ao lado do programa."
    Return
  ${EndIf}

  Delete "$INSTDIR\portable.txt"
  WriteUninstaller "$INSTDIR\Desinstalar.exe"

  ${If} $Atualizar == "1"
    StrCpy $OptDesktop ${BST_UNCHECKED}
    StrCpy $OptMenu ${BST_UNCHECKED}
    StrCpy $OptGuia ${BST_UNCHECKED}
  ${EndIf}

  ${If} $OptDesktop == ${BST_CHECKED}
    CreateShortcut "$DESKTOP\${APPDISPLAY}.lnk" "$INSTDIR\${APPEXE}"
  ${EndIf}
  ${If} $OptMenu == ${BST_CHECKED}
  ${OrIf} $OptGuia == ${BST_CHECKED}
    CreateDirectory "$SMPROGRAMS\${APPDISPLAY}"
  ${EndIf}
  ${If} $OptMenu == ${BST_CHECKED}
    CreateShortcut "$SMPROGRAMS\${APPDISPLAY}\${APPDISPLAY}.lnk" "$INSTDIR\${APPEXE}"
    CreateShortcut "$SMPROGRAMS\${APPDISPLAY}\Desinstalar ${APPDISPLAY}.lnk" "$INSTDIR\Desinstalar.exe"
  ${EndIf}
  ${If} $OptGuia == ${BST_CHECKED}
    CreateShortcut "$SMPROGRAMS\${APPDISPLAY}\Guia de uso.lnk" "$INSTDIR\doc\pt_BR\help.html"
  ${EndIf}

  ; Menu de contexto e Enviar para, só no modo instalar. A cópia portátil já retornou.
  !insertmacro RegisterAssoc ".jpg"
  !insertmacro RegisterAssoc ".jpeg"
  !insertmacro RegisterAssoc ".png"
  !insertmacro RegisterAssoc ".webp"
  !insertmacro RegisterAssoc ".gif"
  !insertmacro RegisterAssoc ".bmp"
  !insertmacro RegisterAssoc ".tif"
  !insertmacro RegisterAssoc ".tiff"
  !insertmacro RegisterAssoc ".heic"
  !insertmacro RegisterAssoc ".heif"
  !insertmacro RegisterAssoc ".mp4"
  !insertmacro RegisterAssoc ".avi"
  !insertmacro RegisterAssoc ".mkv"
  !insertmacro RegisterAssoc ".webm"
  !insertmacro RegisterAssoc ".mov"
  !insertmacro RegisterAssoc ".flv"
  !insertmacro RegisterAssoc ".wmv"
  !insertmacro RegisterAssoc ".mpeg"
  !insertmacro RegisterAssoc ".mpg"
  !insertmacro RegisterAssoc ".3gp"
  !insertmacro RegisterAssoc ".ogv"
  !insertmacro RegisterAssoc ".ts"
  !insertmacro RegisterAssoc ".m4v"
  !insertmacro RegisterAssoc ".divx"
  !insertmacro RegisterAssoc "image"
  !insertmacro RegisterAssoc "video"
  CreateShortcut "$APPDATA\Microsoft\Windows\SendTo\${SENDTO}" "$INSTDIR\${APPEXE}"

  WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APPDISPLAY}"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${APPVERSION}"
  WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "Leandro Maruci"
  WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${APPEXE}"
  WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" "$\"$INSTDIR\Desinstalar.exe$\""
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  FindFirst $0 $1 "$INSTDIR\*.*"
  loop:
    StrCmp $1 "" done
    StrCmp $1 "." next
    StrCmp $1 ".." next
    StrCmp $1 "Dados" next
    StrCmp $1 "Desinstalar.exe" next
    IfFileExists "$INSTDIR\$1\*.*" 0 isfile
      RMDir /r "$INSTDIR\$1"
      Goto next
    isfile:
      Delete "$INSTDIR\$1"
    next:
      FindNext $0 $1
      Goto loop
  done:
    FindClose $0

  Delete "$DESKTOP\${APPDISPLAY}.lnk"
  Delete "$SMPROGRAMS\${APPDISPLAY}\${APPDISPLAY}.lnk"
  Delete "$SMPROGRAMS\${APPDISPLAY}\Desinstalar ${APPDISPLAY}.lnk"
  Delete "$SMPROGRAMS\${APPDISPLAY}\Guia de uso.lnk"
  RMDir "$SMPROGRAMS\${APPDISPLAY}"
  Delete "$APPDATA\Microsoft\Windows\SendTo\${SENDTO}"
  !insertmacro UnregisterAssoc ".jpg"
  !insertmacro UnregisterAssoc ".jpeg"
  !insertmacro UnregisterAssoc ".png"
  !insertmacro UnregisterAssoc ".webp"
  !insertmacro UnregisterAssoc ".gif"
  !insertmacro UnregisterAssoc ".bmp"
  !insertmacro UnregisterAssoc ".tif"
  !insertmacro UnregisterAssoc ".tiff"
  !insertmacro UnregisterAssoc ".heic"
  !insertmacro UnregisterAssoc ".heif"
  !insertmacro UnregisterAssoc ".mp4"
  !insertmacro UnregisterAssoc ".avi"
  !insertmacro UnregisterAssoc ".mkv"
  !insertmacro UnregisterAssoc ".webm"
  !insertmacro UnregisterAssoc ".mov"
  !insertmacro UnregisterAssoc ".flv"
  !insertmacro UnregisterAssoc ".wmv"
  !insertmacro UnregisterAssoc ".mpeg"
  !insertmacro UnregisterAssoc ".mpg"
  !insertmacro UnregisterAssoc ".3gp"
  !insertmacro UnregisterAssoc ".ogv"
  !insertmacro UnregisterAssoc ".ts"
  !insertmacro UnregisterAssoc ".m4v"
  !insertmacro UnregisterAssoc ".divx"
  !insertmacro UnregisterAssoc "image"
  !insertmacro UnregisterAssoc "video"
  DeleteRegKey HKCU "${UNINSTKEY}"
  Delete "$INSTDIR\Desinstalar.exe"
  RMDir "$INSTDIR"
SectionEnd
