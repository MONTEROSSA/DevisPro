from PIL import Image
img = Image.open('/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/Resources/devispro/logo.gif')
img.save('/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/Resources/devispro/icon.ico', format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
print('icon.ico created')