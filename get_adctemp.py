from ._shared_imports import *


def get_adctemp(paths_files, path_results, **kwargs):
  """Validate that ADC calibration monitor graphs are present."""
  status, path_monitor = get_file_regex(
    paths_files, regex=r"(?i).*monitor.*\.root$"
  )
  if not status:
    return False, "FELIS ERROR when finding monitor ROOT file for ADC calibration", None, None, None

  status, chip_paths = find_rootPaths(path_monitor)
  if not status:
    return False, "FELIS ERROR when finding chip paths in ADC monitor ROOT file", None, None, None

  monitor = ROOT.TFile.Open(path_monitor)
  if not monitor or monitor.IsZombie():
    return False, "FELIS ERROR when opening ADC monitor ROOT file", None, None, None

  missing = []
  for chip_path in chip_paths:
    numbers = extract_pathNumbers(chip_path)
    vina_name = "D_B({})_O({})_H({})_DQM_VINA_Chip({})".format(*numbers)
    temp_name = "D_B({})_O({})_H({})_DQM_TEMPSENS_CENTER_Chip({})".format(*numbers)
    directory = monitor.Get(chip_path)
    if not directory.Get(vina_name):
      missing.append(f"{chip_path}/{vina_name}")
    if not directory.Get(temp_name):
      missing.append(f"{chip_path}/{temp_name}")
  monitor.Close()

  if missing:
    return False, "Missing ADC monitor graphs: " + ", ".join(missing), None, None, None

  return True, "", {"ADC_MONITOR_CHIPS": len(chip_paths)}, True, ""
