import os
import shutil

def migrate_old_db():
    for filename in os.listdir('db'):
        if filename.endswith('.json') and not os.path.isdir(os.path.join('db', filename)):
            slug = filename[:-5]
            first_char = slug[0].lower() if slug else 'others'
            if first_char.isalnum():
                folder = first_char
            else:
                folder = 'others'
            os.makedirs(os.path.join('db', folder), exist_ok=True)
            shutil.move(os.path.join('db', filename), os.path.join('db', folder, filename))
    print("Migrasi selesai.")

if __name__ == "__main__":
    migrate_old_db()
