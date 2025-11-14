from PIL import Image, ImageDraw, ImageFont
import os

def create_icons():
    """Tạo icons cho PWA"""
    # Đảm bảo thư mục static tồn tại
    os.makedirs('static', exist_ok=True)
    
    # Màu sắc
    background_color = (102, 126, 234)  # #667eea
    circle_color = (118, 75, 162)       # #764ba2
    text_color = (255, 255, 255)        # white
    
    # Tạo icon 192x192
    size_192 = (192, 192)
    img_192 = Image.new('RGB', size_192, background_color)
    draw_192 = ImageDraw.Draw(img_192)
    
    # Vẽ hình tròn ở giữa
    circle_margin = 20
    circle_bbox = [
        circle_margin, 
        circle_margin, 
        size_192[0] - circle_margin, 
        size_192[1] - circle_margin
    ]
    draw_192.ellipse(circle_bbox, fill=circle_color)
    
    # Vẽ robot emoji (sử dụng font hỗ trợ emoji)
    try:
        # Thử sử dụng font hệ thống
        font_size = 80
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", font_size)
            except:
                font = ImageFont.load_default()
        
        # Vẽ emoji robot
        text = "🤖"
        bbox = draw_192.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size_192[0] - text_width) // 2, (size_192[1] - text_height) // 2)
        draw_192.text(position, text, fill=text_color, font=font)
    except:
        # Fallback: vẽ hình vuông đơn giản nếu không vẽ được emoji
        square_margin = 50
        square_bbox = [square_margin, square_margin, size_192[0]-square_margin, size_192[1]-square_margin]
        draw_192.rectangle(square_bbox, fill=text_color)
    
    img_192.save('static/icon-192.png', 'PNG')
    
    # Tạo icon 512x512
    size_512 = (512, 512)
    img_512 = Image.new('RGB', size_512, background_color)
    draw_512 = ImageDraw.Draw(img_512)
    
    # Vẽ hình tròn ở giữa
    circle_margin_512 = 50
    circle_bbox_512 = [
        circle_margin_512, 
        circle_margin_512, 
        size_512[0] - circle_margin_512, 
        size_512[1] - circle_margin_512
    ]
    draw_512.ellipse(circle_bbox_512, fill=circle_color)
    
    # Vẽ robot emoji
    try:
        font_size_512 = 200
        try:
            font_512 = ImageFont.truetype("arial.ttf", font_size_512)
        except:
            try:
                font_512 = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", font_size_512)
            except:
                font_512 = ImageFont.load_default()
        
        text_512 = "🤖"
        bbox_512 = draw_512.textbbox((0, 0), text_512, font=font_512)
        text_width_512 = bbox_512[2] - bbox_512[0]
        text_height_512 = bbox_512[3] - bbox_512[1]
        position_512 = ((size_512[0] - text_width_512) // 2, (size_512[1] - text_height_512) // 2)
        draw_512.text(position_512, text_512, fill=text_color, font=font_512)
    except:
        # Fallback
        square_margin_512 = 150
        square_bbox_512 = [square_margin_512, square_margin_512, size_512[0]-square_margin_512, size_512[1]-square_margin_512]
        draw_512.rectangle(square_bbox_512, fill=text_color)
    
    img_512.save('static/icon-512.png', 'PNG')
    
    print("✅ Icons created successfully!")
    print("📁 Icons saved in: static/icon-192.png and static/icon-512.png")

if __name__ == "__main__":
    create_icons()
