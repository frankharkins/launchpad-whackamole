def coords_to_midi(coords):
    x, y = coords
    return x + (y*16)

def midi_to_coords(midi):
    x = midi % 16
    y = midi // 16
    return (x, y)

