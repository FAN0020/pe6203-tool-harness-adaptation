import SwiftUI
struct Example: View {
 @State private var items = ["one", "two"]
 var body: some View { List(items, id: \.self) { Text($0) }.onDelete { items.remove(atOffsets: $0) } }
}
