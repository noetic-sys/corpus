/**
 * Exports a table element to CSV by extracting data from the DOM
 */
export function downloadTableAsCSV(tableId: string, separator: string = ',') {
  // Select rows from table_id
  const rows = document.querySelectorAll(`table#${tableId} tr`)

  // Construct csv
  const csv: string[] = []
  for (let i = 0; i < rows.length; i++) {
    const row: string[] = []
    const cols = rows[i].querySelectorAll('td, th')

    for (let j = 0; j < cols.length; j++) {
      // Clean innertext to remove multiple spaces and jumpline (break csv)
      let data = cols[j].textContent?.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ') || ''
      // Escape double-quote with double-double-quote
      data = data.replace(/"/g, '""')
      // Push escaped string
      row.push(`"${data}"`)
    }
    csv.push(row.join(separator))
  }

  const csvString = csv.join('\n')

  // Download it
  const filename = `export_${tableId}_${new Date().toLocaleDateString().replace(/\//g, '-')}.csv`
  const link = document.createElement('a')
  link.style.display = 'none'
  link.setAttribute('target', '_blank')
  link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvString))
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}