# disk-health.ps1

$disks = Get-PhysicalDisk

$result = foreach ($disk in $disks) {

    $rel = $disk | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue

    $labels = Get-Partition -DiskNumber $disk.DeviceId -ErrorAction SilentlyContinue |
              Get-Volume -ErrorAction SilentlyContinue |
              Select-Object -ExpandProperty FileSystemLabel

    if (-not $labels) { $labels = "" }

    [PSCustomObject]@{
        DeviceId              = $disk.DeviceId
        FriendlyName          = $disk.FriendlyName
        VolumeLabel           = ($labels -join ", ")
        BusType               = $disk.BusType
        MediaType             = $disk.MediaType
        ReadErrorsUncorrected = $rel.ReadErrorsUncorrected
        Wear                  = $rel.Wear
        PowerOnHours          = $rel.PowerOnHours
        Temperature           = $rel.Temperature
    }
}

$result | Sort-Object DeviceId | Format-Table -AutoSize
