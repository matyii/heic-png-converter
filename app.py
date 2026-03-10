import os
import sys

from pathlib import Path
from PIL import Image
import pillow_heif

import argparse
from tqdm import tqdm
import multiprocessing
import cpuinfo


def worker(args):
	import pillow_heif
	pillow_heif.register_heif_opener()
	heic_path, export_base, keep_metadata, optimize, src_path_str = args
	src_path = Path(src_path_str)
	if src_path.is_file():
		rel_path = Path(heic_path).name
	else:
		rel_path = Path(heic_path).relative_to(src_path)
	export_path = Path(export_base) / Path(rel_path).parent / (Path(rel_path).stem + '.png')
	export_path.parent.mkdir(parents=True, exist_ok=True)
	try:
		from PIL import Image
		with Image.open(heic_path) as img:
			img_to_save = img
			pnginfo = None
			if optimize:
				if img.mode in ("RGBA", "RGB"):
					img_to_save = img.convert("P", palette=Image.ADAPTIVE, colors=256)
			if keep_metadata and hasattr(img, 'info') and img.info:
				from PIL.PngImagePlugin import PngInfo
				pnginfo = PngInfo()
				for k, v in img.info.items():
					try:
						pnginfo.add_text(str(k), str(v))
					except Exception:
						pass
			save_kwargs = {
				'optimize': optimize,
				'compress_level': 9 if optimize else 6,
			}
			if pnginfo:
				save_kwargs['pnginfo'] = pnginfo
			img_to_save.save(
				export_path,
				'PNG',
				**save_kwargs
			)
		return (str(heic_path), str(export_path), None)
	except Exception as e:
		return (str(heic_path), None, str(e))

def convert_heic_to_png(src_folder, keep_metadata=False, optimize=False):
	pillow_heif.register_heif_opener()
	src_path = Path(src_folder)

	from datetime import datetime
	today_str = datetime.now().strftime('%Y-%m-%d')
	daily_export_base = Path('exports') / today_str

	def process_heic_file(heic_path, export_base, keep_metadata, optimize):
		if src_path.is_file():
			rel_path = heic_path.name
		else:
			rel_path = heic_path.relative_to(src_path)
		export_path = export_base / Path(rel_path).parent / (Path(rel_path).stem + '.png')
		export_path.parent.mkdir(parents=True, exist_ok=True)
		try:
			with Image.open(heic_path) as img:
				img_to_save = img
				pnginfo = None
				if optimize:
					if img.mode in ("RGBA", "RGB"):
						img_to_save = img.convert("P", palette=Image.ADAPTIVE, colors=256)
				if keep_metadata and hasattr(img, 'info') and img.info:
					from PIL.PngImagePlugin import PngInfo
					pnginfo = PngInfo()
					for k, v in img.info.items():
						try:
							pnginfo.add_text(str(k), str(v))
						except Exception:
							pass
				save_kwargs = {
					'optimize': optimize,
					'compress_level': 9 if optimize else 6,
				}
				if pnginfo:
					save_kwargs['pnginfo'] = pnginfo
				img_to_save.save(
					export_path,
					'PNG',
					**save_kwargs
				)
			return (str(heic_path), str(export_path), None)
		except Exception as e:
			return (str(heic_path), None, str(e))

	import time
	start_time = time.time()
	converted_count = 0
	exported_files = []
	failed_files = []

	if src_path.is_file():
		if src_path.suffix.lower() == '.heic':
			export_base = daily_export_base
			_, export_path, error = process_heic_file(src_path, export_base, keep_metadata, optimize)
			if error is None:
				converted_count = 1
				exported_files.append(Path(export_path))
			else:
				failed_files.append((str(src_path), error))
		else:
			print(f"File {src_path} is not a HEIC file.")
	else:
		export_base = daily_export_base / src_path.name
		heic_files = []
		for root, _, files in os.walk(src_path):
			for file in files:
				if file.lower().endswith('.heic'):
					heic_path = Path(root) / file
					heic_files.append(heic_path)

		if len(heic_files) > 0 and convert_heic_to_png.cores > 1:
			with multiprocessing.get_context("spawn").Pool(convert_heic_to_png.cores) as pool:
				results = list(tqdm(pool.imap(worker, [(str(h), str(export_base), keep_metadata, optimize, str(src_path)) for h in heic_files]), total=len(heic_files), desc="Converting HEIC files", unit="file"))
		else:
			results = []
			for heic_path in tqdm(heic_files, desc="Converting HEIC files", unit="file"):
				results.append(process_heic_file(heic_path, export_base, keep_metadata, optimize))

		for heic_path, export_path, error in results:
			if error is None and export_path:
				exported_files.append(Path(export_path))
				converted_count += 1
			elif error:
				failed_files.append((heic_path, error))

	elapsed = time.time() - start_time
	total_size = 0
	for f in exported_files:
		if f.exists():
			total_size += f.stat().st_size
	print("\n--- Conversion Statistics ---")
	print(f"Converted files: {converted_count}")
	print(f"Total export size: {total_size/1024/1024:.2f} MB")
	print(f"Elapsed time: {elapsed:.2f} seconds")
	if failed_files:
		print(f"Failed files: {len(failed_files)}")
		for f, err in failed_files:
			print(f"  {f}: {err}")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Convert HEIC images to PNG.")
	parser.add_argument("input", help="Source folder or HEIC file to convert.")
	parser.add_argument("--keep-metadata", action="store_true", help="Keep metadata in PNG output.")
	parser.add_argument("--optimize", action="store_true", help="Optimize PNG output for smaller file size.")
	try:
		max_cores = cpuinfo.get_cpu_info().get('count', multiprocessing.cpu_count())
	except Exception:
		max_cores = multiprocessing.cpu_count()
	parser.add_argument("--cores", type=int, default=1, metavar=f"[1-{max_cores}]", help=f"Number of CPU cores to use (max {max_cores})")
	# import sys
	cores_flag = any(arg.startswith('--cores') for arg in sys.argv)
	args = parser.parse_args()
	if not cores_flag:
		print(f"Warning: --cores was not specified. Defaulting to 1 core. Use --cores N (max {max_cores}) to set the number of CPU cores.")
	if args.cores > max_cores:
		print(f"Warning: Requested {args.cores} cores, but only {max_cores} available. Using {max_cores}.")
	cores = max(1, min(args.cores, max_cores))
	convert_heic_to_png.cores = cores
	convert_heic_to_png(args.input, keep_metadata=args.keep_metadata, optimize=args.optimize)