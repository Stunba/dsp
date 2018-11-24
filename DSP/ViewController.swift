//
//  ViewController.swift
//  DSP
//
//  Created by Artiom Bastun on 22/11/2018.
//  Copyright © 2018 stunba. All rights reserved.
//

import Cocoa

class ViewController: NSViewController {

    @IBOutlet weak var tableView: NSTableView!
    @IBOutlet weak var checkButton: NSButton!
    @IBOutlet weak var filterButton: NSButton!
    @IBOutlet weak var filterMin: NSTextField!
    @IBOutlet weak var filterMax: NSTextField!
    @IBOutlet weak var distrButton: NSButton!
    @IBOutlet weak var bins: NSTextField!

    let configPath = "/Users/abastun/PycharmProjects/Signals/config.json"
    
    var files: [String] = []

    override func viewDidLoad() {
        super.viewDidLoad()

        tableView.dataSource = self
        tableView.delegate = self
    }

    override var representedObject: Any? {
        didSet {
        // Update the view, if already loaded.
        }
    }

    @IBAction func filterAction(_ sender: Any) {
        guard filterButton.state == .on else { return }
        distrButton.state = .off
    }

    @IBAction func distrAction(_ sender: Any) {
        guard distrButton.state == .on else { return }
        filterButton.state = .off
    }

    @IBAction func plotAction(_ sender: Any) {
        let selectedFiles = files.enumerated().filter { self.tableView.selectedRowIndexes.contains($0.offset) }.map { $0.element }
        guard !selectedFiles.isEmpty else {
            let alert = NSAlert()
            alert.messageText = "Select files"
            alert.alertStyle = .informational
            alert.informativeText = "Select files before plot"
            alert.beginSheetModal(for: view.window!, completionHandler: nil)
            return
        }

        let drawInOneWindow = checkButton.state == .on

        var options: [String : Any] = [
            "draw_in_one_window": drawInOneWindow,
            "files": selectedFiles
        ]

        let filterIsON = filterButton.state == .on
        let distrIsON = distrButton.state == .on

        if filterIsON {
            let min = filterMin.integerValue
            let max = filterMax.integerValue
            guard min < max else {
                let alert = NSAlert()
                alert.messageText = "Filter"
                alert.alertStyle = .informational
                alert.informativeText = "Enter filter min max"
                alert.beginSheetModal(for: view.window!, completionHandler: nil)
                return
            }
            options["filter"] = true
            options["min"] = min
            options["max"] = max
        } else if distrIsON {
            var bins = self.bins.integerValue
            if bins <= 0 {
                bins = 4
            }
            options["distr"] = true
            options["bins"] = bins
        }

        let data = try! JSONSerialization.data(withJSONObject: options, options: .init(rawValue: 0))
        let first = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let url = first.appendingPathComponent("config.json")

        try! data.write(to: url, options: .atomic)

        run()
    }

    @IBAction func openFilesAction(_ sender: Any) {
        let openPanel = NSOpenPanel()
        openPanel.allowsMultipleSelection = true
        openPanel.prompt = "Select"
        openPanel.allowedFileTypes = ["bin"]
        openPanel.begin { _ in
            self.files = openPanel.urls.map { $0.path }
            self.tableView.reloadData()
        }
    }

    func run() {
        guard let scriptPath = Bundle.main.path(forResource: "signals", ofType: "py") else {
            return
        }
//        let scriptPath = "/Users/abastun/PycharmProjects/Signals/signals.py"
        let arguments = [scriptPath]
        let outPipe = Pipe()
        let errPipe = Pipe()

        let task = Process()
        task.launchPath = "/usr/bin/python"
        task.arguments = arguments
        task.standardInput = Pipe()
        task.standardOutput = outPipe
        task.standardError = errPipe

        task.launch()
        task.waitUntilExit()

        let data = outPipe.fileHandleForReading.readDataToEndOfFile()
        let error = errPipe.fileHandleForReading.readDataToEndOfFile()
        print(String(data: data, encoding: String.Encoding.ascii)!)
        print(String(data: error, encoding: String.Encoding.ascii)!)

        let exitCode = task.terminationStatus
        if (exitCode != 0) {
            print("ERROR: \(exitCode)")
        }
    }

    func runScript() {
        let scriptPath = "/Users/abastun/PycharmProjects/Signals/signals.py"

        let arguments = ["-l", "-c", "/usr/bin/python \(scriptPath)"]

//        let env = ProcessInfo.processInfo.environment
//        let shel = env["SHELL"]
//        print(shel!)

        let outPipe = Pipe()
        let errPipe = Pipe()

        let task = Process()
        task.launchPath = "/bin/zsh"
        task.arguments = arguments
        task.standardInput = Pipe()
        task.standardOutput = outPipe
        task.standardError = errPipe
        do {
            try task.run()
        } catch {
            print(error)
            return
        }
//        task.launch()
        task.waitUntilExit()

        let data = outPipe.fileHandleForReading.readDataToEndOfFile()
        let error = errPipe.fileHandleForReading.readDataToEndOfFile()
        print(String(data: data, encoding: String.Encoding.ascii)!)
        print(String(data: error, encoding: String.Encoding.ascii)!)

        let exitCode = task.terminationStatus
        if (exitCode != 0) {
            print("ERROR: \(exitCode)")
        }
    }
}

extension ViewController: NSTableViewDataSource, NSTableViewDelegate {
    func numberOfRows(in tableView: NSTableView) -> Int {
        return files.count
    }

    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        guard let cell = tableView.makeView(withIdentifier: NSUserInterfaceItemIdentifier(rawValue: "Cell"), owner: nil) as? NSTableCellView else {
            return nil
        }
        cell.textField?.stringValue = URL(fileURLWithPath: files[row]).pathComponents.last!
        return cell
    }
}

