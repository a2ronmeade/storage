import array
import re
import ROOT

def ADCCal_CSV_to_ROOT(
                        moduleName,       # TFPX / TBPX / TEPX naming convention
                        rootPath,         # "Detector/Board_0/OpticalGroup_0/Hybrid_0"
                                          # Board, OpticalGroup, Hybrid numbers found/passed by OSU-GUI / Dirigent
                        inputCSV,         # power-supply Vin CSV: line 0 = times (s), line 1 = voltages (V)
                        outputDir,        # Output directory
                        chipMonitorROOT,  # path to the Run..._MonitorDQM_Board_....root file Ph2_ACF wrote
                        chip              # chip ID, e.g. 12/13/14/15
                        ):
  # --- power supply Vin, from CSV ---
  with open(inputCSV) as file:
    line = file.readlines()
  if len(line) < 2:
    raise ValueError(f"Expected time and voltage rows in {inputCSV}")
  v_Time_PS = [float(i) for i in line[0].strip().split(",")]; v_Time_PS = array.array('d', v_Time_PS)
  v_Vin_PS  = [float(i) for i in line[1].strip().split(",")]; v_Vin_PS  = array.array('d', v_Vin_PS)
  if len(v_Time_PS) != len(v_Vin_PS):
    raise ValueError(f"Time and voltage rows have different lengths in {inputCSV}")
  ps_start = v_Time_PS[0]
  v_Time_PS = array.array("d", [value - ps_start for value in v_Time_PS])

  # --- chip Vin, from the MonitorDQM.root file Ph2_ACF wrote during the run ---
  match = re.search(r"Board_(\d+)/OpticalGroup_(\d+)/Hybrid_(\d+)", rootPath)
  if not match:
    raise ValueError(f"Invalid monitor ROOT path: {rootPath}")
  board, og, hybrid = match.groups()

  monFile = ROOT.TFile.Open(chipMonitorROOT)
  rootPath = rootPath.rstrip("/")
  chipPath = "{0}/Chip_{1}".format(rootPath, chip)
  vinName = "D_B({0})_O({1})_H({2})_DQM_VINA_Chip({3})".format(board, og, hybrid, chip)
  tempName = "D_B({0})_O({1})_H({2})_DQM_TEMPSENS_CENTER_Chip({3})".format(
      board, og, hybrid, chip
  )
  g_Vin_Chip = monFile.Get("{0}/{1}".format(chipPath, vinName))
  g_Temp_Chip = monFile.Get("{0}/{1}".format(chipPath, tempName))
  if not g_Vin_Chip or not g_Temp_Chip:
    monFile.Close()
    missing = "VINA" if not g_Vin_Chip else "TEMPSENS_CENTER"
    raise RuntimeError(f"Could not find {missing} graph for chip {chip} in {chipMonitorROOT}")
  vin_points = [
      (g_Vin_Chip.GetX()[point], g_Vin_Chip.GetY()[point])
      for point in range(g_Vin_Chip.GetN())
  ]
  temp_points = [
      (g_Temp_Chip.GetX()[point], g_Temp_Chip.GetY()[point])
      for point in range(g_Temp_Chip.GetN())
  ]
  monFile.Close()

  # Monitor timestamps are Unix time; convert them to elapsed seconds.
  monitor_start = min(vin_points[0][0], temp_points[0][0])
  vin_x = array.array("d", [point[0] - monitor_start for point in vin_points])
  vin_y = array.array("d", [point[1] for point in vin_points])
  temp_x = array.array("d", [point[0] - monitor_start for point in temp_points])
  temp_y = array.array("d", [point[1] for point in temp_points])
  g_Vin_Chip = ROOT.TGraph(len(vin_x), vin_x, vin_y)
  g_Vin_Chip.SetName("g_Vin_Chip{0}".format(chip))
  g_Temp_Chip = ROOT.TGraph(len(temp_x), temp_x, temp_y)
  g_Temp_Chip.SetName("g_Temp_Chip{0}".format(chip))

  # --- power supply graph ---
  g_Vin_PS = ROOT.TGraph(len(v_Time_PS), v_Time_PS, v_Vin_PS)
  g_Vin_PS.SetTitle("; Time (s); Vin (V)")
  g_Vin_PS.SetName("g_Vin_PowerSupply_Chip{0}".format(chip))
  g_Vin_PS.SetMarkerStyle(8)
  g_Vin_PS.SetMarkerColor(ROOT.kBlue)
  g_Vin_PS.SetLineColor(ROOT.kBlue)
  g_Vin_PS.SetMinimum(0.0)
  g_Vin_PS.SetMaximum(3.0)

  g_Vin_Chip.SetMarkerStyle(22)
  g_Vin_Chip.SetMarkerSize(1.4)
  g_Vin_Chip.SetMarkerColor(ROOT.kRed)
  g_Vin_Chip.SetLineColor(ROOT.kRed)
  g_Vin_Chip.SetLineWidth(3)
  g_Vin_Chip.SetLineStyle(2)

  c_Vin = ROOT.TCanvas("c_Vin_Chip{0}".format(chip), "c_Vin_Chip{0}".format(chip), 800, 800)
  g_Vin_PS.Draw("ALP")
  g_Vin_Chip.Draw("LP SAME")
  c_Vin.Update()
  g_Vin_PS.GetYaxis().SetRangeUser(0.0, 3.0)
  c_Vin.Modified()
  c_Vin.Update()

  legend = ROOT.TLegend(0.65, 0.15, 0.88, 0.3)
  legend.AddEntry(g_Vin_PS, "Power Supply", "lp")
  legend.AddEntry(g_Vin_Chip, "Chip (VINA)", "lp")
  legend.Draw()

  svgPath = "{0}/ADCCal_Module_{1}_Chip{2}.svg".format(outputDir, moduleName, chip)
  c_Vin.SaveAs(svgPath)

  c_Temp = ROOT.TCanvas("c_Temp_Chip{0}".format(chip), "c_Temp_Chip{0}".format(chip), 800, 800)
  g_Temp_Chip.SetTitle("; Time (s); Temperature")
  g_Temp_Chip.SetName("g_Temp_Chip{0}".format(chip))
  g_Temp_Chip.SetMarkerStyle(21)
  g_Temp_Chip.SetMarkerColor(ROOT.kGreen + 2)
  g_Temp_Chip.SetLineColor(ROOT.kGreen + 2)
  g_Temp_Chip.Draw("APL")
  tempSvgPath = "{0}/ADCCal_Module_{1}_Chip{2}_Temperature.svg".format(
      outputDir, moduleName, chip
  )
  c_Temp.SaveAs(tempSvgPath)

  file = ROOT.TFile(chipMonitorROOT, "UPDATE")
  if not file.GetDirectory(chipPath):
    file.mkdir(chipPath)
  file.cd(chipPath)
  g_Vin_Chip.Write(vinName, ROOT.TObject.kOverwrite)
  g_Temp_Chip.Write(tempName, ROOT.TObject.kOverwrite)
  g_Vin_PS.Write("g_Vin_PowerSupply_Chip{0}".format(chip), ROOT.TObject.kOverwrite)
  c_Vin.Write("c_Vin", ROOT.TObject.kOverwrite)
  c_Temp.Write("c_Temperature", ROOT.TObject.kOverwrite)
  c_Vin.Write("{0}_Canvas".format(vinName), ROOT.TObject.kOverwrite)
  c_Temp.Write("{0}_Canvas".format(tempName), ROOT.TObject.kOverwrite)
  file.Close()
