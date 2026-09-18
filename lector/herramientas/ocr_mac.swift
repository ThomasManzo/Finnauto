// ocr_mac.swift — OCR con el motor del propio macOS (Vision). Sin instalar nada.
//
// Se usa para extractos que llegan como ESCANEO (imagen adentro del PDF, sin texto),
// como el del Banco Nación. Recibe PNGs y devuelve, por cada pedazo de texto que
// reconoce, su posición en la página (x, y, ancho, alto en fracción 0-1, con el
// origen ABAJO a la izquierda como lo devuelve Vision) y el texto. Con la posición,
// `lector/extractos.py` arma las columnas (fecha / descripción / débito / crédito / saldo).
//
// Uso:  swift lector/herramientas/ocr_mac.swift pagina1.png pagina2.png > salida.tsv
// Salida: una línea por texto → archivo \t x \t y \t w \t h \t confianza \t texto

import Foundation
import Vision
import AppKit

let args = Array(CommandLine.arguments.dropFirst())
if args.isEmpty {
    FileHandle.standardError.write("uso: swift ocr_mac.swift imagen.png [...]\n".data(using: .utf8)!)
    exit(1)
}

for ruta in args {
    guard let img = NSImage(contentsOfFile: ruta),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("no pude abrir \(ruta)\n".data(using: .utf8)!)
        continue
    }
    let pedido = VNRecognizeTextRequest()
    pedido.recognitionLevel = .accurate
    pedido.usesLanguageCorrection = false      // números y códigos: que no "corrija" nada
    pedido.recognitionLanguages = ["es-ES", "en-US"]
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([pedido]) } catch {
        FileHandle.standardError.write("fallo OCR en \(ruta): \(error)\n".data(using: .utf8)!)
        continue
    }
    let nombre = (ruta as NSString).lastPathComponent
    for obs in pedido.results ?? [] {
        guard let mejor = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        let texto = mejor.string.replacingOccurrences(of: "\t", with: " ")
        print("\(nombre)\t\(b.origin.x)\t\(b.origin.y)\t\(b.size.width)\t\(b.size.height)\t\(mejor.confidence)\t\(texto)")
    }
}
