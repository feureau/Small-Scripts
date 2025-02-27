Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create a new form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Video Encoder GUI"
$form.Size = New-Object System.Drawing.Size(400, 400)

# Resolution Label and Drop-down
$resLabel = New-Object System.Windows.Forms.Label
$resLabel.Text = "Select Resolution:"
$resLabel.Location = New-Object System.Drawing.Point(20, 20)
$form.Controls.Add($resLabel)

$resDropdown = New-Object System.Windows.Forms.ComboBox
$resDropdown.Location = New-Object System.Drawing.Point(150, 20)
$resDropdown.Size = New-Object System.Drawing.Size(200, 20)
$resDropdown.Items.Add("8K")
$resDropdown.Items.Add("4K")
$resDropdown.SelectedIndex = 0
$form.Controls.Add($resDropdown)

# QVBR Value Label and TextBox
$qvbrLabel = New-Object System.Windows.Forms.Label
$qvbrLabel.Text = "Enter QVBR Value (default 18):"
$qvbrLabel.Location = New-Object System.Drawing.Point(20, 60)
$form.Controls.Add($qvbrLabel)

$qvbrInput = New-Object System.Windows.Forms.TextBox
$qvbrInput.Text = "18"
$qvbrInput.Location = New-Object System.Drawing.Point(200, 60)
$form.Controls.Add($qvbrInput)

# HDR 4K CheckBox
$hdr4kCheckbox = New-Object System.Windows.Forms.CheckBox
$hdr4kCheckbox.Text = "Encode HDR 4K AV1"
$hdr4kCheckbox.Location = New-Object System.Drawing.Point(20, 100)
$form.Controls.Add($hdr4kCheckbox)

# HDR 8K Horizontal CheckBox
$hdr8kHorzCheckbox = New-Object System.Windows.Forms.CheckBox
$hdr8kHorzCheckbox.Text = "Encode HDR 8K Horizontal AV1"
$hdr8kHorzCheckbox.Location = New-Object System.Drawing.Point(20, 140)
$form.Controls.Add($hdr8kHorzCheckbox)

# HDR 8K Vertical CheckBox
$hdr8kVertCheckbox = New-Object System.Windows.Forms.CheckBox
$hdr8kVertCheckbox.Text = "Encode HDR 8K Vertical HEVC"
$hdr8kVertCheckbox.Location = New-Object System.Drawing.Point(20, 180)
$form.Controls.Add($hdr8kVertCheckbox)

# Crop Type Label and Drop-down
$cropLabel = New-Object System.Windows.Forms.Label
$cropLabel.Text = "Select Crop Type (8K Vertical):"
$cropLabel.Location = New-Object System.Drawing.Point(20, 220)
$form.Controls.Add($cropLabel)

$cropDropdown = New-Object System.Windows.Forms.ComboBox
$cropDropdown.Location = New-Object System.Drawing.Point(200, 220)
$cropDropdown.Size = New-Object System.Drawing.Size(150, 20)
$cropDropdown.Items.Add("Wide")
$cropDropdown.Items.Add("Academic")
$cropDropdown.SelectedIndex = 0
$form.Controls.Add($cropDropdown)

# Process Button
$processButton = New-Object System.Windows.Forms.Button
$processButton.Text = "Start Encoding"
$processButton.Location = New-Object System.Drawing.Point(150, 280)
$processButton.Add_Click({
    # Collect values from the form elements
    $resolution = $resDropdown.SelectedItem
    $qvbrValue = $qvbrInput.Text
    $encodeHdr4k = $hdr4kCheckbox.Checked
    $encodeHdr8kHorz = $hdr8kHorzCheckbox.Checked
    $encodeHdr8kVert = $hdr8kVertCheckbox.Checked
    $cropType = $cropDropdown.SelectedItem

    # Display a message with the selected options
    [System.Windows.Forms.MessageBox]::Show("Starting Encoding with the following options:`nResolution: $resolution`nQVBR Value: $qvbrValue`nHDR 4K: $encodeHdr4k`nHDR 8K Horz: $encodeHdr8kHorz`nHDR 8K Vert: $encodeHdr8kVert`nCrop Type: $cropType")

    # Example of executing a batch command (add full encoding script here)
    Start-Process cmd.exe -ArgumentList "/c echo Resolution=$resolution QVBR=$qvbrValue" -NoNewWindow -Wait
})
$form.Controls.Add($processButton)

# Show the form
$form.ShowDialog()
