LJ
j   6  99 B  X�6  99 B= K  readfilesettingssettings_filenamefileexistsbmdH   6  99 9 BK  settingssettings_filenamewritefilebmd�  %6   B X�6  B 8   X� 	 X� 5 =L X� 	 X	� 5 =L X�8 L K   sample_duration�time_scale sample_duration�tonumberstring	type0 ��<��� 
 	 E6   9B9  X�
   X�  X�:: X�+ L X�:: X�:: X�+ L X
�:: X�:: X�+ L 6 :B' 6 :B' 6 :	B' &   X	�  )   X�  '  &X�'  &+   J Version  v- or later is required to run this script.tostringAppGetVersionapp�  z  X�+ +   )  )  )  9	 9
#	
		 			6
 9

9 9#B

 
!

'  X-�9 9#	 X�9 9#X�6 ' B6 9"	# B "	$  X� "  6 9!"
#B" 
  X� X�' 6 99 9#B$6 9#B 6 9# B 6 9#  B'	   
  X� X�6
 9'      B X	�6
 9'    B !   J %02d:%02d:%02d%02d:%02d:%02d%s%02dformatstring;
floorMDropFrame can only be used with framerates that are a multiple of 29.97.
error:	ceil	mathsample_durationtime_scalexѬ������ p  6  9  X�+ X�+ )�9B99#" #9#L time_scalesample_durationiif�� 
C6  9  X�+ X�+ )�9B-     B6 9B6 9B6  	 6
 9

 B


B' )	  	 X	�6	 9		'  B		   X	�6	 9		 B		 X	�6	 9		'    D	 X	�6	 9		'	    D	 K  �%s %0dm %0.03fs%s %0dm %0ds	%0dhformatstring
floor	mathsample_durationiif�x�  -    	 
 B  X�6  9
 ) B 5 = ====L �
color
titletimestamptruncated_frame
frame has_noteshas_errorssubstring�   4   9 ' ' B   & 9'  &BX�6 9
  BER�L insert
table	(.-)gmatch	%%%1([^%w])	gsub?   
  9  ' ' B 9 ' ' D 	%s+$	^%s+	gsubz  -    '  B' 6  BH�- 
 B	 )
  
	 X	�	 
 ' &	FR�-  D �� 
pairs
g   
   X
�  )   X�6  9  ' D X�L  K  (.-)([^\/]-%.?([^%.\/]*))$
matchstringN  
   X
�  )   X�-  9   BL X�L  K  �GetPathPartsN  
   X
�  )   X�-  9   BL X�L  K  �GetPathPartsi  
   X�  )   X	�-  9   B 9' D X�L  K  �(.+)%..+
matchGetPathPartsN  
   X
�  )   X�-  9   BL X�L  K  �GetPathParts� 
 6    9 B A X�9 X�9-  9	&	L ER�K  �OutputFilenameTargetDir
JobIdGetRenderJobListipairs�  
  6   9  ' B 6 9' 9 9 9 9	 9
 9	 D secmin	hourday
month	year&[%04d-%02d-%02d].[%02d.%02d.%02d]formatstring*t	dateosb 
    9  B
  X
� ) )��M�  9 8	9		BO�K  IDRemoveChildGetChildren�   -'    9 ' ' B 9' ' B 9' BX� )	  	 X�6 9	
 ) ) B X� 6	 9	
	'  ' & B	&	X� 	 &	ER�L d%0formatsubstring.(.-)%zgmatch%1(.)%z%1
%0%0 .	gsubP  )��8    X� 8 9 9 !X�9 !L truncated_frame�  	 6  6 9 B X�+ X�+ ' ' B6 9  9 '	 
 B  D {seconds}	gsubformatstring%%0.03f%%d
floor	mathiif�6
\�'  '  '  '    9 B4  4    9 B!!6  BH�
  X�   X� X�9 X	� X� X�6 9  BFR� )   X��6 9 B6	 9
-   8  B) ) B X�+ X�+ ' 4  + 3 6  BX��86 9!
!  X!�+! X"�+! '"  9#B6  9"
"  X"�+" X#�+" '#  -$ 9&B$ A ! )"  "! X!�!  )"   "! X!�+! X"�+! " $ & '' ( ((B$'% & B"$" 9""'% '& B" X#�#" $ &"$#X#O� X#�#" $  &"$#X#I� X##� ! X#�#" 6$	 9$$'& ' 6(   X*�+* X+�+* '+ . 9,'/ '0 B, A()  B$&"$#X#/�#" -$ 6&	 9&&'( ) *  B& A$ &"$#X#$� X#"� ! X#�#" 6$	 9$$'& '  6(   X*�+* X+�+* '+ . 9,'/ '0 B, A() B$&"$#X#
�#" -$ 6&	 9&&'( )  * B& A$ &"$## ##-$ !&' ( )" 9*+ B$<$#ERm )   X*�  X�:9 X�  X"�:9  X�- )     '!   B+ ="6 9 )  B6	 9'#  :9-  ! " # +$ B A  )  X�6	 9'$  B + - ! B)  4  4  3% 3& 6 ! BX"��9$'# $ X%�$ =$'#$ & '" ( B$-% '$ ( B%6&( 6(	 9(('*) +%#++B( A& ' "' X'�&X'� &)'
 %' X'
�+' =''#' ''( '** 9+#,% B(<('9'+#'' 	'  X'
�+' =''#' ''6(	 9(('*, 9+#B(<('-' 9)-#9*.#!)*)* B''''(  ))  )' X)	�6)	 9))'+/ 9,-#9-.#!,-,-' B)() 6)	 9))'+0 , -" . -/ 1$ 2 631 33 B/-0  92-# 223 4 +5 B01( -2 93#823293#94+#B)) 6)	 9))'+2 , 9-#9.+#0. 9..'1 '2 B. A)) ) ))5*5 '+3 6,4 ." B,&+,+=+6*=&7*9++#-+ 9++'. '/ B+=+8*-+ 9,#8+,+=+9*9+"#=+:*9+'#=+;*<*)E"R"q )     X�6	 9'!< " B 6 ! BX"�$ %# '&= &&$E"R"� )     X�6	 9'!> " B 6 ! BX"�$ %# '&= &&$E"R"�X�'? '   
 X��9@
+ =A9B
+ =A- 9@
B- 9B
B 	  X�9@
 9C	 9D	5E B A9B
 9C	 9D	5F B A9G
+ =H9I
+ =HXA�)  ) M7�87J 9@
 9C	 9D	5K 6J 96=66J 97=76J 98=8'L 6 J 9 9 '!M &!=NB A9B
 9C	 9D	5P 6J 96' O & =66J 97=76J 98=8'Q 6  6"J 9";"'#R '$S B '!M &!=NB AO�9G
+ =H9I
+ =H9@
+ =A9B
+ =A9T
 'V &=U )    X� )   X�9W
6	 9'X -  -	  B=U9Y
+ =ZX�9W
'  =U9Y
+ =Z '=  9'[ '  B&2  �L ����������	%b<>HiddenMessagePanelE<div style='color: %s;'>%s</div><div style='color: %s;'>%s</div>TextEditMessages<div></div>	HTMLTextEditChapterstransparent#FF0000`		                QLabel
		                {
                            border: 1px solid   SelectionStyleSheet/;
		                }
                    W		                QLabel
		                {
			                background-color:   timelineItemSaveAsButtonEnabledCopyButton Weight Weight
LabelAddChildMiniTimelineSelectionUpdatesEnabledMiniTimelineNo markersB%s<div><b>Error:</b> Chapter titles shouldn't be empty</div>

Y%s<div><b>Error:</b> Minimum length for a YouTube video chapter is 10 seconds</div>
HasErrorsHasNotes
ColorToolTipWeightID  tostringTimelineItem%s%s %s
is_last_chapter�%s<div title='Chapter: %d/%d
Duration: %s
REC TC: %s%s' style='color: #FFFFFF;'><span style='color: %s;'>%s</span>&nbsp;%s</div>*

Timestamp is %d frames (%dms) earlytruncated_frame
frame.<div>* Chapter title at %s is empty</div>
title5<div>* Chapter at %s is {seconds} seconds.</div>	%.0ftonumberhas_errors  I%s<div><b>Error:</b> YouTube requires at least three chapters</div>
]%s<div><b>Note:</b> Added required chapter at %s (add a marker at %s to set title)</div>has_notes
Lemon
00:0000:00:00timestampMarker Notes + Name
%s %s%s%s%sformatMarker Name + NotesMarker NotesMarker Name&nbsp; 	gsub#%	note	nameiifipairs 
Start00substring	sortinsert
table
colorAll
pairsGetStartFrameGetMarkers ���   V6  9 XG�6 9' 6 9' B-  9- 9	B 9
B 9'	 '
 B- B A6 9' ' 6 9'	 
   B A6 9 ' B6 9 B6 96 9	 '
 B A 6 9 B6 6 9	 B' 	  &	B6 6 9	 B A X
�6 6 9   B'   &BK  � ��renameremoveCouldn't rename file executeassert
close
concat
writeoutputa	openiomove /y "%s" "%s" >nulchcp 65001@echo off	pack
table_ 	gsub
lowerfilename GetFilenameWithoutExtension	TEMPgetenv%s\%s.%s.batformatstringWindowsosffij   6  9   B6  9 B6  9 B6  9 BK  
close
writeoutput	openio� ,3  6 9 X!�6 9' 6 9'	 B-  9	-
 9


B
 9B
 9' ' B-	 B	 A   	 B-    BX�     BK  � ���_ 	gsub
lowerfilename GetFilenameWithoutExtension	TEMPgetenv%s\%s.%s.tmpformatstringWindowsosffi �  -6  9  B  X�-  9  B6 9'  -	  9		 B	-
 B
 B-   	 B-  B X�X�-    ' B6	 6 9'
   B A K  �����*Saved YouTube video chapters to: "%s"
printa GetFilenameWithoutExtension%s%s.[Backup].%s.%sformatstringGetPathPartsfileexistsbmd] 	  6    9 B A X�9 X�L ER�+  L 
JobIdGetRenderJobListipairs�  (-  + = - - 9 6 996 996 99- 
 9B-	 	 9		B	-
 - - 6 B6 9	'
 =-  + = -   9BK  �  ����RecalcLayoutStatusPanelGetEndFrameGetStartFrameLineEditSeparatorLineEditPrefixCurrentTextComboBoxChapterTitlewindowItems	TextUpdatesEnabled�  >-  + = - - 6 999 6 996 99- 
 9B-	 	 9		B	-
 - - 6 B6 9	'
 =6 96 99 X�6 99 X�+ X�+ =6 96 99=-  + = -   9BK  �  ����RecalcLayoutLabelSeparatorMarker Notes + NameMarker Name + NotesComboBoxChapterTitleVisibleStatusPanelGetEndFrameGetStartFrameLineEditSeparatorLineEditPrefix	TextCurrentTextComboBoxMarkerswindowItemsUpdatesEnabled� 
 $-  + = - - 6 996 999 6 99- 
 9B-	 	 9		B	-
 - - 6 B-  + = -   9	BK  �  ����RecalcLayoutGetEndFrameGetStartFrameLineEditSeparator	TextComboBoxChapterTitleCurrentTextComboBoxMarkerswindowItemsUpdatesEnabled� 
 $-  + = - - 6 996 996 999 - 
 9B-	 	 9		B	-
 - - 6 B-  + = -   9	BK  �  ����RecalcLayoutGetEndFrameGetStartFrame	TextLineEditPrefixComboBoxChapterTitleCurrentTextComboBoxMarkerswindowItemsUpdatesEnabled� 	 6  96 99B6 9' =-   9BK  �RecalcLayoutCopied to Clipboard	TextStatusPanelPlainTextTextEditChapterswindowItemssetclipboardbmd�  W-  9 9 	  X�6 9 X�6 9' B' &X�6 9' B'	 &6
 9' -  9B A' 6  9  5	 =	B  X,�- - 6 996	 9		9		6
 9

9

6 99-  9B-  9B- - B
- 9 B-	   B	-	  9	 	=	-	  	 9		B	6	 9		'
 =
	K    � ��  
SavedStatusPanelsave_settingsGetPathPartsGetEndFrameGetStartFrameLineEditSeparator	TextLineEditPrefixComboBoxChapterTitleCurrentTextComboBoxMarkerswindowItemsFReqS_Title FReqS_FilterFReqB_SavingRequestFileapp Save YouTube Video ChaptersGetName%s.[Chapters].txtformatstring/	HOME\USERPROFILEgetenvWindowsosffilastSavedPathsettings &  -   9 BK  �ExitLoop�  !-  9 6 99=-  9 6 99=-  9 6 99	=-  9 6 99	=
-   9B-  9BK   �ExitLoopsave_settingsLineEditSeparatorseparator	TextLineEditPrefixprefixComboBoxChapterTitlechapterTitlesCurrentTextComboBoxMarkerswindowItemsmarkerssettings�  9  	  X�6 9 9BX�9   X�9  	 X�6 9 9BK  OkButton
ClickCancelButtonwindowItemsKey���������>   6  9 9BK  
ClickCancelButtonwindowItems�%}�5  5 	 95
 5 =
5 =
 95
 5	 = 95  95 =5 =B> 95 5 =' -  ' &=B> 95 5 =5 =B> 95 6 9' - 9 - 9!B- 9"B=#5$ =B ?  B> 95%  95& =5' =B> 95( 5) =' -  ' &=B> 95* 5+ =5, =B ? B> 95-  95. ==5/ =B> 9051 B> 952 =53 =B> 9054 B> 955 56 =57 =B ? B> 94  9859 B> 95:  9;5< B> 9;5= B ? B ? B> 9>4  95? B> 95@ B ? B> 95A  985B 5C =5D =B> 95F 5E =5G =B ? B> 95H  95I 5J =B> 9K)  ) B> 9;5L B> 9;5M B ?  B ? B ? B+ =N
 9O5P B
 9QB7R 6R 9S
 9T- B6R 9S-	 9	V	9	W	=	U6R 9X
 9T- B6R 9X-	 9	V	9	Y	=	U6R 9Z-	 9	V	9	\	=	[6R 9]-	 9	V	9	^	=	[6R 9Z6	R 9	_	9	#	=	#6R 9]6	R 9	X	9	U		a X	�6	R 9	X	9	U		b X	�+	 X
�+	 =	`6R 9c6	R 9	]	9	`	=	`6R 9d
 9eB6R 9f
 9gB+ =N9h9S3	j =	i9h9X3	k =	i9h9Z3	m =	l9h9]3	n =	l9h9o3	q =	p9h9r3	s =	p9h9t3	u =	p9h9v3	w =	p9h9x3	z =	y9h9x3	| =	{ 6	R 2  �J �� ����� 
Close KeyPressYouTubeChapters OkButton CancelButton SaveAsButton ClickedCopyButton  TextChanged  ActivatedTextOnSetFocusTextEditChapters
LowerMiniTimelineLabelSeparatorMarker Notes + NameMarker Name + NotesVisibleLabelPrefixseparatorLineEditSeparatorprefix	TextLineEditPrefixchapterTitlesComboBoxChapterTitlemarkerssettingsCurrentTextAddItemsComboBoxMarkerswindowItemsGetItems  ��SetFixedSizeUpdatesEnabled IDOkButtonWeight 	TextOKDefault IDCancelButtonWeight 	TextCancel	HGap AlignVCenter 	TextIDStatusPanel Weight   ���      ���P  �P Weight IDTextEditMessagesReadOnly HiddenIDMessagePanel Spacing IDMiniTimelineSelectionStyleSheet�                        QLabel
                        {
						    background-color: transparent;
                            border: 1px none #FF0000;
						    border-radius: 0px;
                            max-height: 10px;
                            margin-top: 8px;
					    }
                    Weight Margin  Spacing IDMiniTimelineStyleSheet�		                    QLabel
		                    {
			                    background-color: #777777;
                                border: 1px solid #000000;
                                border-radius: 0px;
                                max-height: 8px;
                                margin-top: 9px;
		                    }
                        WeightMargin 
Stack IDSaveAsButtonWeight 	TextSave As IDCopyButtonWeight 	Text	CopyButton Weight  IDTextEditChaptersWeightReadOnlyTextEdit  _  _ Weight  Weight ����IDLineEditSeparator AlignVCenterAlignRight 	TextSeparatorIDLabelSeparatorStyleSheet�                        QLabel
                        {
                            margin-left: 8px;
                        }
                    Weight  Weight ����IDLineEditPrefixLineEdit AlignVCenterAlignRight IDLabelPrefix	TextPrefixToolTip�Add any text you want before each chapter.

Supports the following variables:
% is the current chapter index
# is the total number of chapters

To add leading zeros to variables, add the variable multiple times. Example:
Chapter %%/##: Weight  Weight   _  _ Weight  ActivatedText IDComboBoxChapterTitleWeight AlignVCenterAlignRight Weight	TextChapter Title Weight  AlignTopToolTipversionfilename GetFilenameWithoutExtension<%s v%s
Go to the forum post associated with this scriptformatstring 	TextU<a href='https://tiny.cc/youtubevideochapters' style='color: #4376A1;'>About</a>IDInfoLinkOpenExternalLinksWeight   8  8 Weight StyleSheet;
		                }O		                QComboBox
		                {
			                color:  ActivatedText IDComboBoxMarkersWeightComboBoxAlignment AlignVCenterAlignRightMaximumSize Weight	TextMarkers
Label Weight HGroupMinimumSize    ��VGroupEvents KeyPress
CloseWindowFlags Window IDYouTubeChaptersStyleSheet6		QComboBox
		{
			padding: 1px 0px 2px 10px;
		}WindowTitle YouTube Video Chapters PlusWindowModalityApplicationModalAddWindow  d���  d	������������������������&  -   9 BK  �ExitLoop| 9  	  X�-  9 9BX�9   X�9  	 X�-  9 9BK  �
ClickOkButtonKey���������0  -  9  9BK  �
ClickOkButton�*o 9 5 5 =5 =	 94
  95 -  9	- 9
B' - 9' &=5 =B>
 95 = 5 =B>
 9)  ) B>
 95  9)  ) B> 95 B> 9)  ) B ?  B ? B>	 95
 B ? B 9B9+ =9 95 B9 95  B9 9!B9+ =9"9#3% =$9"93' =&9"93) =(  2  �J � � 
Close KeyPress ClickedOkButtonOn
Lower  ��SplashBorder  ��ResizeUpdatesEnabledSplashGetItems StyleSheetborder: 1px solid black;IDSplashBorder IDOkButtonWeight 	TextOKDefaultButton	HGap Weight HGroup	VGap AlignCenter WeightAlignment AlignCenter	Text for DaVinci Resolveversion vfilename GetFilenameWithoutExtension WeightStyleSheetHcolor: white; font-weight: bold; font-size: 14px; margin-top: 10px;
LabelVGroupEvents KeyPress
CloseWindowFlags SplashScreen Spacing IDSplashWindowModalityApplicationModalMarginAddWindow����	��������� 3 ��5  6  9) ' B9 9' B= 6 9	B 9
B 9' B = 6 
  X�+ X�+ = 6 9	B 9
B 9' B
  X�6   X�+ X�+ = 5 = 6  9) ' B9 9' B 9' ' B= 6   X�6 = 3 = 3 =   9 B4  6 9 9 ) ) B54 5! >5" >5# *  <5$ >5% >5& * <5' >5( * <5) >05* >25+ * <5, ><5- >H5. * <5/ >`50 >d51 * <52 >x33 =566 97'8 '9 ': '	; B66 97'< '= '	> '
? '@ 'A 'B 'C 'D 'E 'F 'G 'H 'I 'J 'K 'L B'M 'N 5O 5	P 3
Q 3R 3S 3T 3U 3V 3W 3X 3Z =Y3\ =[3^ =]3` =_3b =a3c 3d 3e 3f 3g 3h 3i 3j 3k 3l 
 'm 5n B  X��6o   9pB  9qB! 9rB" 9 5% 9#s'&t B# A # 9!s'$u B!!v X!�+! X"�+! 9"  " X#?�6"w "x X"|�" $ 6% B" " X#v�% 9#yB#& 9$zB$9%{"#% X%�9#{"9%|"&$%& X%�9$|"% ' 9( 9(}(9) 9)~)9* 9**9+ 9+�+,# -$ .  /! B%
9&Y( * 6+ B( A& 6)� 9)�)'+� ,& 9-_/' B- A)* ,) -% B*9* =&�*,  9* B*X"@�6" 9"�"6# 9#�#%" B#$ & '  (! )" *# B$& ( 9) 9)})9* 9*~*9+ 9++9, 9,�,/ 9-yB-0 9.zB./  0! 1" 2% B&($ 9&�$B&(# 9&�#B&($ 9&�$B&X�6 9�6 9�! B  " # $ B $  9"� B"$ 9"�B"$  9"� B"6� B2  �K  collectgarbage	HideRunLoop	ShowUIDispatcherUIManagerlastSavedPath%s%s.[Chapters].txtformatstringseparatorprefixchapterTitlesmarkersMarkOutMarkInGetEndFrameGetStartFrame
error1timelineDropFrameTimecodetimelineFrameRateGetSettingGetCurrentTimelineGetCurrentProjectGetProjectManagerresolve    Resolve           GetExtension  GetFilenameWithoutExtension GetFilename GetPath GetPathParts         Apricotrgb(255, 168, 51)	Bluergb(67, 118, 161)Orangergb(235, 110, 1)Purplergb(153, 114, 160)Violetrgb(208, 86, 141)Tanrgb(185, 175, 151)	Navyrgb(0, 82, 120)
Beigergb(196, 160, 124)	Tealrgb(1, 152, 153)
Brownrgb(153, 102, 1)Chocolatergb(140, 90, 63)
Olivergb(95, 153, 33)	Pinkrgb(255, 68, 200)	Limergb(159, 198, 21)Yellowrgb(212, 173, 31)
Greenrgb(68, 143, 101) 	Cyanrgb(0, 206, 208)	Bluergb(0, 127, 227)FrameIOrgb(240, 157, 0)
Creamrgb(245, 235, 225)
Cocoargb(110, 81, 67)	Sandrgb(196, 145, 94)
Lemonrgb(220, 233, 90)	Mintrgb(114, 219, 0)Skyrgb(146, 226, 253)Lavenderrgb(161, 147, 200)	Rosergb(255, 161, 185)Fuchsiargb(192, 46, 111)Purplergb(144, 19, 254)	Pinkrgb(255, 68, 200)Redrgb(225, 36, 1)Yellowrgb(240, 157, 0)
Greenrgb(0, 173, 0)#FF8C8Crgb(146, 146, 146)
Cream
Cocoa	Sand
Lemon	MintSkyLavender	RoseFuchsiaPurple	PinkRedYellow
Green	Cyan	BlueAllMarker Notes + NameMarker Name + NotesMarker NotesMarker Name	pack
tableget_frame_rate_data    sample_durationdtime_scale�] sample_duration�time_scale�� sample_durationdtime_scale�N sample_durationdtime_scale�K sample_duration�time_scale�� sample_durationdtime_scale�8 sample_durationdtime_scale�. sample_duration�time_scale�� sample_durationdtime_scale�' sample_durationdtime_scale�% sample_duration�time_scale�� sample_durationdtime_scale� sample_duration�time_scale�� sample_durationdtime_scale� sample_durationdtime_scale� sample_duration�time_scale�� sample_durationdtime_scale� sample_durationdtime_scale�subconfigpackagesave_settings load_settings was_triggeredstatusjobsettings_filename.settings	.lua	gsubsettings chapterTitlesMarker NamemarkersAllseparatorprefixlastSavedPathstarted_from_script_menustarted_from_fuscriptapp"started_from_internal_consolescript	find
lowergetappnamebmdfilename version	1.01^.*%@(.*)
matchsourceSgetinfo
debug������߁��������������������������߂�������� 