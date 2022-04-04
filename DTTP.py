"""
TODO:
Make more levels (easier ones)
"""



#SECTION 1: Defining variables
import numpy.random.common
import numpy.random.bounded_integers
import numpy.random.entropy
import numpy,json,os,sys,time,threading,copy,random,urllib.request
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']="hide"
import pygame

sys.stdout=open("GameLogs.txt","w")
pygame.init()
Font=pygame.font.Font("Fonts/rainyhearts.ttf",16)
win=pygame.Surface((256,144))
RenderType="Level"
RenderText="Press V to jump and X to dash."
RenderTextList=open("RenderTextList.txt").read().splitlines()
RenderTextListIndexes=list(range(len(RenderTextList)))
WallLocation=0
HighScore=int(open("High Score.txt").read())
TrueWin=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
Sounds={
	"Death":pygame.mixer.Sound("Sounds/Death.mp3"),
	"Dash":pygame.mixer.Sound("Sounds/Dash.mp3"),
	"Jump":pygame.mixer.Sound("Sounds/Jump.mp3"),
	"Level Complete":pygame.mixer.Sound("Sounds/Complete.mp3"),
}
TileProperties={
	"(0, 0, 255, 255)":{
		"Name": "Rift",
		"Attributes":["Rift"],
		},
	"(127, 0, 255, 255)":{
		"Name": "Solid",
		"Attributes":["Solid"],
		},
	"(0, 0, 0, 255)":{
		"Name": "Air",
		"Attributes":[]
		},
	"(255, 255, 0, 255)":{
		"Name": "Harmful",
		"Attributes":["Harmful"],
		},
	"(255, 0, 0, 255)":{
		"Name": "Dash Block",
		"Attributes":["Dash"],
		},
}

def GetColors(Color=None,Mode=None,UseOnlyGoodColors=False,Image=None):
	global GameColors#
	if Image!=None:
		GameColors=[Image.get_at((i,0)) for i in range(4)]
		return GameColors
	if UseOnlyGoodColors:
		ColorList=pygame.image.load("Colors.png")
		R=random.randint(0,ColorList.get_height()-1)
		GameColors=[ColorList.get_at((i,R)) for i in range(4)]
		return GameColors
	if Mode==None:
		#Mode=random.choice(["monochrome","monochrome-dark","monochrome-light","analogic","complement","analogic-complement","triad","quad"])
		#Mode=random.choice(["monochrome","monochrome-dark","monochrome-light"])
		Mode="monochrome-light"
	if Color==None:
		Color="".join([random.choice(list("1234567890abcdef")) for i in range(6)])
		#Color=random.choice([Color+"ff","ff"+Color])
		#Color=random.choice([Color+"00","00"+Color])
	print(f"Color: {Color}, Mode: {Mode}")
	page=urllib.request.urlopen(f"https://www.thecolorapi.com/scheme?hex={Color}&mode={Mode}&count=4&format=json")
	X=json.loads(page.read())
	Y=[(X["colors"][i]["rgb"]["r"],X["colors"][i]["rgb"]["g"],X["colors"][i]["rgb"]["b"]) for i in range(4)]
	GameColors=Y
	return Y
def GetDeathText():
	global RenderTextList,RenderTextListIndexes
	Y=random.randint(0,len(RenderTextList)-1)
	X=RenderTextList.pop(Y)
	pygame.mixer.Sound(f"Death Voice Lines/Don't Touch the Purple (TTS) Export 1 Track {RenderTextListIndexes.pop(Y)+2} Render 1.wav").play()
	if len(RenderTextList)==0:
		RenderTextList=open("RenderTextList.txt").read().splitlines()
		RenderTextListIndexes=list(range(len(RenderTextList)))
	return X.lower()
#GenerateColorImage()

#Section 2: Defining Classes

class MenuClass:
	def __init__(self,Choices=["Default Menu","Test"],SelectedItem=0):
		self.Choices=Choices
		self.SelectedItem=SelectedItem
		self.SelectedItemTransition=SelectedItem
	def __call__(self):
		global RenderType,RenderMenu
		RenderType="Menu"
		RenderMenu=self
		print("A")
		while 1:
			X=self.Loop(*InputHandler())
			if X!="_CONTINUE":
				return X
	def Loop(self,Events,Keys):
		for Event in Events:
			if Event.type==pygame.QUIT:
				return "Exit"
			if Event.type==pygame.KEYDOWN:
				if Event.key==pygame.K_ESCAPE:
					return "Exit"
				if Event.key==pygame.K_DOWN:
					if self.SelectedItem!=len(self.Choices)-1:
						self.SelectedItem+=1
				if Event.key==pygame.K_UP:
					if self.SelectedItem!=0:
						self.SelectedItem-=1
				if Event.key==pygame.K_v:
					return self.Choices[SelectedItem]
		return "_CONTINUE"
	def Render(self):
		self.SelectedItemTransition-=self.SelectedItem%len(self.Choices)
		self.SelectedItemTransition/=1.1
		self.SelectedItemTransition+=self.SelectedItem%len(self.Choices)
		win.fill(0)
		for i,j in enumerate(self.Choices):
			T=Font.render(j,0,(255,255,255))
			win.blit(T,(win.get_width()/2-T.get_width()/2,win.get_height()/2-T.get_height()/2+100*(i-self.SelectedItemTransition)**3))
		ScaleWindow()
class CameraClass:
	def __init__(self):
		self.Pos=[0,0]
		self.RenderPos=[0,0]
		self.ScreenHalf=[128,72]
		self.ShakeTime=0
	def __call__(self,TileCoords):
		return numpy.add(numpy.subtract(TileCoords,self.RenderPos),self.ScreenHalf)
	def UpdatePosition(self,Speed=1.1):
		global WallLocation
		TP=Player.Pos
		TP=numpy.clip(TP,self.ScreenHalf,numpy.subtract(Level.Image.get_size(),self.ScreenHalf))
		self.Pos=numpy.add(numpy.divide(numpy.subtract(self.Pos,TP),Speed),TP)
		self.RenderPos=copy.deepcopy(self.Pos)
		if self.ShakeTime>0:
			self.ShakeTime-=1
			ShakeIntensity=2
			self.RenderPos=numpy.add(self.RenderPos,[random.randint(-int(self.ShakeTime/ShakeIntensity),int(self.ShakeTime/ShakeIntensity)),random.randint(-int(self.ShakeTime/ShakeIntensity),int(self.ShakeTime/ShakeIntensity))])
		if WallLocation<self.RenderPos[0]-128:
			WallLocation=self.RenderPos[0]-128
	def Shake(self,Time):
		self.ShakeTime=Time
class PlayerClass:
	def __init__(self):
		self.XV=0
		self.YV=0
		self.HitBoxSize=[1,1]
		self.CoyoteTime=10
		self.Grounded=0
		self.WallBound=0
		self.WallJumpTimer=0
		self.WallSide=-1
		self.Direction=1
		self.DoubleJump=0
		self.Pos=[16,0]
		while self.Colliding():
			self.Pos[1]+=8
		while not self.Colliding():
			self.Pos[1]+=8
		self.Pos[1]-=8
		self.RespawnPoint=copy.deepcopy(self.Pos)
		self.RenderPos=copy.deepcopy(self.Pos)
	def __call__(self,Events,Keys):
		#Jumping
		for Event in Events:
			if Event.type==pygame.KEYDOWN:
				if Event.key==pygame.K_v and self.Grounded:
					self.YV=-4
					self.Grounded=0
					Sounds["Jump"].play()
				elif Event.key==pygame.K_v and self.WallBound:
					self.YV=-7
					self.WallBound=0
					self.WallJumpTimer=20
					self.XV=-self.WallSide*5
					Sounds["Jump"].play()
				elif Event.key==pygame.K_x and self.DoubleJump:
					self.XV=self.Direction*13
					self.YV=0
					self.WallJumpTimer=7
					self.DoubleJump-=1
					Camera.Shake(10)
					Sounds["Dash"].play()
				elif Event.key==pygame.K_v and self.DoubleJump:
					self.YV=-5
					self.DoubleJump-=1
					Camera.Shake(10)
					Sounds["Dash"].play()

		#Calculate Direction
		X=numpy.sign(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])
		if X!=0:
			self.Direction=X

		#Physics
		if self.WallJumpTimer>0: #Post Wall Jump Physics
			#self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])*0.1
			#self.XV/=1.05
			#self.YV+=0.4
			self.XV/=1.1
			self.YV/=1.1
		elif self.Grounded==self.CoyoteTime: #Grounded Physics
			self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])*1.5
			self.XV/=2
			self.YV+=0.05
		elif self.WallBound==self.CoyoteTime: #Wall Slide Physics
			self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])*1.5
			self.XV/=2
			self.YV/=1.2
			self.YV+=0.4
		else:
			if abs(self.YV)<0.5: #Apex Physics
				if Keys[pygame.K_v]:
					self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])
					self.XV/=1.5
					self.YV+=0.05
				else:
					self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])
					self.XV/=1.5
					self.YV+=0.1
			else: #Air Physics
				if Keys[pygame.K_v]:
					self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])
					self.XV/=1.5
					self.YV+=0.2
				else:
					self.XV+=(Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT])
					self.XV/=1.5
					self.YV+=0.4

		#Apply Velocity
		if any(["Rift" in i["Attributes"] for i in self.GetCollisions()]):
			self.DoubleJump=2
		self.Pos[1]+=self.YV
		if self.CollidingWithHarm():
			self.Die()
			return "Restart"
		if self.Colliding():
			if self.YV>0:
				self.Grounded=self.CoyoteTime
				self.DoubleJump=2
			self.Pos[1]-=self.YV
			self.YV=0
		self.Pos[0]+=self.XV
		if self.CollidingWithHarm():
			self.Die()
			return "Restart"
		if self.Colliding() or self.CollidingWithDashBlock():
			self.Pos[0]-=self.XV
			self.WallSide=numpy.sign(self.XV)
			self.XV=0
			self.WallBound=self.CoyoteTime
		elif self.WallBound>0:
			self.WallBound-=1
		elif self.Grounded>0:
			self.Grounded-=1
		if self.Pos[0]<WallLocation and WallLocation>16:
			self.Die()
			return "Restart"
		self.YV/=1.05
		if self.WallJumpTimer>0:
			self.WallJumpTimer-=1
		if self.WallJumpTimer==0:
			if any([("Dash" in i["Attributes"]) and self.DoubleJump!=2 for i in self.GetCollisions()]):
				self.WallJumpTimer=1
				self.XV*=1.1
				self.YV*=1.1
		self.RenderPos=copy.deepcopy(self.Pos)
	def Colliding(self):
		return any(["Solid" in i["Attributes"] for i in self.GetCollisions()])
	def CollidingWithDashBlock(self):
		return any([("Dash" in i["Attributes"]) and self.DoubleJump==2 for i in self.GetCollisions()])
	def CollidingWithHarm(self):
		return any(["Harmful" in i["Attributes"] for i in self.GetCollisions()])
	def GetCollisions(self):
		C0=numpy.floor(numpy.subtract(numpy.divide(self.Pos,8),numpy.divide(self.HitBoxSize,2)))
		C1=numpy.floor(numpy.add(numpy.divide(self.Pos,8),numpy.divide(self.HitBoxSize,2)))
		CS=numpy.add(numpy.subtract(C1,C0),1)
		L=[]
		for x in range(int(CS[0])):
			for y in range(int(CS[1])):
				try:
					if int(x+C0[0])<0 or int(y+C0[1])<0:
						continue
					L.append(Level.Tiles[int(x+C0[0])][int(y+C0[1])])
				except:
					pass
		return L
	def Die(self):
		global Level,GameColors
		Sounds["Death"].play()
		self.Pos=copy.deepcopy(self.RespawnPoint)
		self.XV=0
		self.YV=0
		Player.DoubleJump=2
		Level=World.Levels[CurrentLevel]

class WorldClass:
	def __init__(self):
		global LightColors,DarkColors
		GetColors(Image=pygame.image.load("Game Colors.png"))
		self.Levels=[]
		L=[]
		Files=[]
		for (dirpath, dirnames, filenames) in os.walk("Levels"):
			Files.extend(dirpath+"\\"+i for i in filenames)
			break
		for i in Files:
			if i.endswith(".png"):
				L.append(LevelClass(i))
		#for i in self.LevelNameList:
			#L.append(LevelClass(Name+"/TileMaps/"+i,Name+"/Renders/"+i))
		G=[]
		for i in range(20):
			for j in range(len(L)):
				G.append(j)
			for j in range(len(L)):
				self.Levels.append(L[G.pop(random.randint(0,len(G)-1))])
	def __call__(self):
		pass
class LevelClass:
	def __init__(self,Name):
		print(Name)
		self.TileMap=pygame.image.load(Name)
		self.TileMap.set_colorkey((255,255,255))
		self.Name=Name
		self.Tiles=[]
		self.EntranceHeight=None
		self.ExitHeight=None
		for x in range(self.TileMap.get_width()):
			self.Tiles.append([])
			for y in range(self.TileMap.get_height()):
				self.Tiles[x].append(copy.deepcopy(TileProperties[str(self.TileMap.get_at((x,y)))]))
				if x==0 and self.EntranceHeight==None and y<self.TileMap.get_height()-3:
					if all([TileProperties[str(self.TileMap.get_at((x,y+i)))]["Name"]=="Air" for i in range(4)]):
						self.EntranceHeight=y
				elif x==self.TileMap.get_width()-1 and self.ExitHeight==None and y<self.TileMap.get_height()-3:
					if all([TileProperties[str(self.TileMap.get_at((x,y+i)))]["Name"]=="Air" for i in range(4)]):
						self.ExitHeight=y
				"""X=self.TileMap.get_at((x,y))
				Y=X[0]+X[1]+X[2]
				Y/=255*2.9
				Y=min(int(Y),1)
				Y*=255
				self.TileMap.set_at((x,y),(Y,Y,Y))"""
		self.Image=pygame.transform.scale(self.TileMap,(self.TileMap.get_width()*8,self.TileMap.get_height()*8)).convert()
		image_pixel_array=pygame.PixelArray(self.Image)
		try:image_pixel_array.replace((0,0,0),GameColors[1])
		except:pass
		try:image_pixel_array.replace((127,0,255),GameColors[0])
		except:pass
		try:image_pixel_array.replace((255,255,0),GameColors[3])
		except:pass
		"""ColorEffect=100
		X=self.Image.copy()
		X.fill((200-ColorEffect+hash(Name)%ColorEffect,200-ColorEffect+int(hash(Name)/ColorEffect)%ColorEffect,200-ColorEffect+int(hash(Name)/ColorEffect**2)%ColorEffect))
		Y=self.Image.copy()
		Y.fill((hash(Name)%ColorEffect,int(hash(Name)/ColorEffect)%ColorEffect,int(hash(Name)/ColorEffect**2)%ColorEffect))
		self.Image.blit(X,(0,0),special_flags=pygame.BLEND_MULT)
		self.Image.blit(Y,(0,0),special_flags=pygame.BLEND_ADD)"""
	def __call__(self):
		pass

#SECTION 3: Defining gameplay functions

def InputHandler():
	return pygame.event.get(),pygame.key.get_pressed()
def MainThread():
	global Frames,StartTime
	StartTime=time.time()
	Frames=0
	while 1:
		try:
			G=Loop(*InputHandler())
		except IndexError:
			return "Complete"
		if G=="Restart":
			return "Restart"
		if G=="Exit":
			sys.exit()
		Frames+=1
		X=StartTime+Frames/60-time.time()
		if X>0:
			time.sleep(X)
def Loop(Events,Keys):
	global Level,CurrentLevel,OldLevelPos,LevelChange,Frames,WallLocation,StartTime
	for Event in Events:
		if Event.type==pygame.QUIT:
			return "Exit"
		if Event.type==pygame.KEYDOWN:
			if Event.key==pygame.K_ESCAPE:
				return "Exit"
			if Event.key==pygame.K_r:
				return "Restart"
	if Keys[pygame.K_g]:
		Player.XV=0
		Player.YV=0
		Player.Pos[0]+=Keys[pygame.K_RIGHT]-Keys[pygame.K_LEFT]
		Player.Pos[1]+=Keys[pygame.K_DOWN]-Keys[pygame.K_UP]
		Player.RenderPos=copy.deepcopy(Player.Pos)
	else:
		X=Player(Events,Keys)
		if X=="Restart":
			return "Restart"
	CPos=numpy.subtract(Camera.Pos,Player.Pos)
	PosChange=[0,0]
	if Player.Pos[0]>Level.Image.get_width():
		#PosChange=[-Level.Image.get_width(),12*8-Level.Image.get_height()]
		CurrentLevel+=1
		LevelChange=1
		print(f"Level {CurrentLevel}: {time.time()-StartTime}")
		A=Level.ExitHeight
		C=-Level.Image.get_width()
		Level=World.Levels[CurrentLevel]
		B=Level.EntranceHeight
		PosChange=[C,(B-A)*8]
		WallLocation+=C
		if WallLocation<C:
			WallLocation=C
	if Player.Pos[0]<0:
		Player.Pos[0]=0
		Player.XV=0
		"""CurrentLevel-=1
		LevelChange=-1
		B=Level.EntranceHeight
		Level=World.Levels[CurrentLevel]
		C=Level.Image.get_width()
		A=Level.ExitHeight
		PosChange=[C,(A-B)*8]"""
	if PosChange!=[0,0]:
		Player.Pos=numpy.add(Player.Pos,PosChange)
		OldLevelPos=[PosChange[0]+numpy.sign(PosChange[0]),PosChange[1]+numpy.sign(PosChange[1])]
		Player.RespawnPoint=copy.deepcopy(Player.Pos)
		Sounds["Level Complete"].play()
		Player.DoubleJump=2
		Camera.Pos=numpy.add(CPos,Player.Pos)
		Player.RenderPos=Player.Pos
		for i in range(30):
			Frames+=1
			X=StartTime+Frames/60-time.time()
			if X>0:
				time.sleep(X)
			Camera.UpdatePosition(1.3)
	Level()
	WallLocation+=(CurrentLevel+1)/30
	#Camera.Pos=numpy.add(CPos,Player.Pos)
	Camera.UpdatePosition()

#SECTION 4: Defining render functions

def ScaleWindow():
	pygame.transform.scale(win,(TrueWin.get_width(),TrueWin.get_height()),TrueWin)
	pygame.display.update()
def ChromaticAberration(Pos):
	ColorScreens=[win.copy(),win.copy(),win.copy()]
	ColorScreens[0].fill((255,0,0))
	ColorScreens[1].fill((0,255,0))
	ColorScreens[2].fill((0,0,255))
	ColorScreens[0].blit(win,numpy.subtract([0,0],Pos),special_flags=pygame.BLEND_MULT)
	ColorScreens[1].blit(win,(0,0),special_flags=pygame.BLEND_MULT)
	ColorScreens[2].blit(win,Pos,special_flags=pygame.BLEND_MULT)
	win.fill(0)
	for i in range(3):
		win.blit(ColorScreens[i],(0,0),special_flags=pygame.BLEND_ADD)
def RenderThread():
	while 1:
		try:
			if RenderType=="Level":
				RenderLevel()
			elif RenderType=="Menu":
				RenderMenu.Render()
			else:
				RenderWorldIntro()
		except:
			pass
def RenderLevel():
	global Frames
	win.fill(GameColors[3])
	win.blit(Level.Image,Camera((0,0)))
	try:
		win.blit(World.Levels[CurrentLevel-LevelChange].Image,Camera(OldLevelPos))
	except:
		pass
	G=abs(Player.XV)-abs(Player.YV)
	G/=5
	G=2**G
	pygame.draw.rect(win,GameColors[2],[Camera(numpy.subtract(Player.RenderPos,numpy.multiply(Player.HitBoxSize,[int(4*G),int(4/G)]))),numpy.add(numpy.multiply(Player.HitBoxSize,[int(8*G),int(8/G)]),1)])
	pygame.draw.rect(win,GameColors[3],[(Camera((0,0))[0],0),(WallLocation,win.get_height())])
	ChromaticAberration(numpy.subtract(Camera.Pos,Camera.RenderPos))
	try:
		#win.blit(Font.render(str(int(time.time()*100-StartTime*100)/100),0,GameColors[2]),(0,0))
		win.blit(Font.render(f"Level {CurrentLevel+1}",0,GameColors[2]),(0,0))
	except:
		pass
	#win.blit(X,(0,0),special_flags=pygame.BLEND_MULT)
	ScaleWindow()
def RenderWorldIntro():
	win.fill(0)
	#TODO: Fix Color
	T=Font.render(RenderText,0,(255,255,255))
	T2=Font.render(f"High Score: Level {HighScore}",0,(127,0,255))
	win.blit(T,(win.get_width()/2-T.get_width()/2,win.get_height()/2-T.get_height()/2))
	win.blit(T2,(win.get_width()/2-T2.get_width()/2,0))
	ScaleWindow()
	pass

#SECTION 5: Starting the game
def Main():
	global World,CurrentLevel,Level,Camera,Player,RT,OldLevelPos,RenderType,WallLocation,RenderText,HighScore
	pygame.mixer.music.load(f"Music/OST.mp3")
	pygame.mixer.music.play(-1)
	pygame.mixer.music.set_volume(1)
	RT=threading.Thread(target=RenderThread)
	RT.daemon=1
	RT.start()
	pygame.mixer.Sound("Death Voice Lines/Don't Touch the Purple (TTS) Export 1 Track 1 Render 1.wav").play()
	RenderType="World Intro"
	pygame.time.delay(2300)
	RenderText="Don't Touch the Purple"
	X="Restart"
	while X=="Restart":
		WallLocation=0
		OldLevelPos=[1000,1000]
		RenderType="World Intro"
		World=WorldClass()
		CurrentLevel=0
		Level=World.Levels[CurrentLevel]
		Camera=CameraClass()
		Player=PlayerClass()
		pygame.time.delay(300)
		RenderType="Level"
		X=MainThread()
		if X=="Complete":
			return
		if CurrentLevel+1>HighScore:
			HighScore=CurrentLevel+1
			open("High Score.txt","w").write(str(HighScore))
		RenderText=GetDeathText()
if __name__=="__main__":
	#print(MenuClass(["One","Two","Three","Four","Five"])())
	Main()
#v