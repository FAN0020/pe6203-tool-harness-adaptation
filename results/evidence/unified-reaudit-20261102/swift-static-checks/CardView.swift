import SwiftUI
struct CardView: View {
    @ViewBuilder let content: () -> some View

    var body: some View {
        VStack {
            content()
        }
        .padding()
        .background(.white)
    }
}
