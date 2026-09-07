try:
    from PIL import Image, ImageDraw, ImageFont
    print("PIL OK", Image.__version__)
except Exception as e:
    print("PIL FEHLT:", e)
