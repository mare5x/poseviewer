from poseviewer import run

if __name__ == '__main__':
    run()


# TODO create efficient mechanism for loading large amounts of images (>3000)
# TODO fix, so the app shows the correct icon in the taskbar
# TODO draw tool
# TODO save image (with transformation applied)
# TODO delete option
# TODO implement incremental sequence slideshow
# TODO on full screen auto hide everything and show it only when hovering over it with the mouse

# def get_img(path, index):
#     if index >= len(scandir.listdir(path)):
#         index -= len(scandir.listdir(path))

#     for i, j in enumerate(scandir.listdir(path)):
#         if i == index:
#             return j
