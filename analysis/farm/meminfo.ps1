# meminfo.ps1 -- dot-source-able RAM helper for the farm.
# WMI/CIM, systeminfo and Get-Counter are ALL denied for this standard user
# account on this box, so we P/Invoke GlobalMemoryStatusEx (kernel32), which
# needs no privileges at all. Get-FarmMem returns TotalMB / AvailMB / PctFree.
if (-not ('FarmMem.Native' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace FarmMem {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Auto)]
  public class MEMORYSTATUSEX {
    public uint dwLength;
    public uint dwMemoryLoad;
    public ulong ullTotalPhys;
    public ulong ullAvailPhys;
    public ulong ullTotalPageFile;
    public ulong ullAvailPageFile;
    public ulong ullTotalVirtual;
    public ulong ullAvailVirtual;
    public ulong ullAvailExtendedVirtual;
    public MEMORYSTATUSEX() { this.dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX)); }
  }
  public static class Native {
    [DllImport("kernel32.dll", CharSet=CharSet.Auto, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool GlobalMemoryStatusEx([In, Out] MEMORYSTATUSEX lpBuffer);
  }
}
'@
}
function Get-FarmMem {
  $m = New-Object FarmMem.MEMORYSTATUSEX
  [void][FarmMem.Native]::GlobalMemoryStatusEx($m)
  [pscustomobject]@{
    TotalMB   = [math]::Round($m.ullTotalPhys / 1MB, 0)
    AvailMB   = [math]::Round($m.ullAvailPhys / 1MB, 0)
    PctUsed   = [int]$m.dwMemoryLoad
    PctFree   = [math]::Round(100.0 * $m.ullAvailPhys / $m.ullTotalPhys, 1)
    PageAvailMB = [math]::Round($m.ullAvailPageFile / 1MB, 0)
  }
}
